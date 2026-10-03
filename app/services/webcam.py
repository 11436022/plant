from __future__ import annotations

import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db import models
from app.services.email import send_email
from app.services.files import FrameMetadata, build_public_image_url, create_safe_upload_path, validate_image_content


def validate_webcam_frame(content: bytes, content_type: str | None) -> FrameMetadata:
    return validate_image_content(content, content_type)


class AlertConsensusTracker:
    """Require repeated matching diagnoses before allowing an automatic alert."""

    def __init__(self) -> None:
        self._states: dict[tuple[int, str, str], dict] = {}
        self._lock = threading.Lock()

    def evaluate(self, user_id: int, diagnosis: dict, now: datetime | None = None, *,
                 session_id: str = "legacy", region_id: str = "full-frame") -> dict:
        current_time = now or datetime.now(timezone.utc)
        category = str(diagnosis.get("category", "")).lower()
        confidence = float(diagnosis.get("confidence") or 0.0)
        source = diagnosis.get("grounding_source")
        is_grounded_anomaly = (
            category in {"disease", "pest"}
            and confidence >= settings.WEBCAM_ALERT_CONFIDENCE
            and source in {"disease_database", "pest_database"}
            and not diagnosis.get("requires_review", True)
        )

        with self._lock:
            stale_seconds = max(settings.WEBCAM_ALERT_COOLDOWN_SECONDS, 3600)
            for key, value in list(self._states.items()):
                if (current_time - value["last_seen"]).total_seconds() > stale_seconds:
                    del self._states[key]
            key = (user_id, session_id, region_id)
            if key not in self._states and len(self._states) >= 10000:
                raise HTTPException(status_code=429, detail="Too many active monitoring regions.")
            state = self._states.setdefault(
                key,
                {
                    "fingerprint": None,
                    "streak": 0,
                    "last_alert_fingerprint": None,
                    "last_alert_at": None,
                    "last_seen": current_time,
                },
            )

            gap = (current_time - state["last_seen"]).total_seconds()
            if gap > max(settings.WEBCAM_SAMPLE_INTERVAL_SECONDS * 3, 1800):
                state["fingerprint"] = None
                state["streak"] = 0
            state["last_seen"] = current_time
            if not is_grounded_anomaly:
                state["fingerprint"] = None
                state["streak"] = 0
                return self._response(False, state, "not_a_grounded_anomaly")

            fingerprint = (
                diagnosis.get("crop_name"),
                category,
                diagnosis.get("status_name"),
            )
            if state["fingerprint"] == fingerprint:
                state["streak"] += 1
            else:
                state["fingerprint"] = fingerprint
                state["streak"] = 1

            cooldown_active = False
            if state["last_alert_fingerprint"] == fingerprint and state["last_alert_at"]:
                elapsed = (current_time - state["last_alert_at"]).total_seconds()
                cooldown_active = elapsed < settings.WEBCAM_ALERT_COOLDOWN_SECONDS

            triggered = (
                state["streak"] >= settings.WEBCAM_ALERT_CONSECUTIVE_MATCHES
                and not cooldown_active
            )
            if triggered:
                state["last_alert_fingerprint"] = fingerprint
                state["last_alert_at"] = current_time

            reason = "triggered" if triggered else "cooldown" if cooldown_active else "collecting_consensus"
            return self._response(triggered, state, reason)

    @staticmethod
    def _response(triggered: bool, state: dict, reason: str) -> dict:
        return {
            "triggered": triggered,
            "streak": state["streak"],
            "required_matches": settings.WEBCAM_ALERT_CONSECUTIVE_MATCHES,
            "reason": reason,
        }


alert_consensus = AlertConsensusTracker()


def save_alert_image(content: bytes, image_format: str) -> Path:
    suffix = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp"}[image_format]
    image_path = create_safe_upload_path(f"webcam-{uuid.uuid4().hex}{suffix}")
    image_path.write_bytes(content)
    return image_path


def create_webcam_alert(
    *,
    db: Session,
    user: models.User,
    diagnosis: dict,
    image_path: Path,
    consecutive_matches: int,
    session_id: str = "legacy",
    region_id: str = "full-frame",
) -> models.WebcamAlert:
    """Stage an alert; the caller must serialize it and commit the transaction."""
    crop = db.query(models.Crop).filter(models.Crop.crop_name == diagnosis["crop_name"]).first()
    if not crop:
        raise RuntimeError("Grounded webcam diagnosis has no matching crop record.")

    alert = models.WebcamAlert(
        user_id=user.user_id,
        crop_id=crop.crop_id,
        category=diagnosis["category"],
        status_name=diagnosis["status_name"],
        confidence=diagnosis["confidence"],
        consecutive_matches=consecutive_matches,
        image_url=str(image_path.as_posix()),
        email_sent=False,
        session_id=session_id,
        region_id=region_id,
        requires_review=diagnosis.get("requires_review", True),
        grounding_source=diagnosis.get("grounding_source", "legacy_unverified"),
        reference_source=diagnosis.get("reference_source"),
        reference_url=diagnosis.get("reference_url"),
        reference_record_id=diagnosis.get("reference_record_id"),
    )
    db.add(alert)
    db.flush()
    db.refresh(alert)
    return alert


def send_webcam_alert_email(
    *, db: Session, alert_id: int, recipient: str | None, diagnosis: dict, consecutive_matches: int,
) -> bool:
    """Notify after persistence, using cached values and a separate status transaction."""
    if not recipient:
        return False
    try:
        send_email(
            to_email=recipient,
            subject=f"Plant Doctor 警報：{diagnosis['status_name']}",
            text_body=(
                f"Webcam 連續 {consecutive_matches} 次辨識到 {diagnosis['crop_name']} "
                f"可能有 {diagnosis['status_name']}，信心值 {diagnosis['confidence']:.0%}。\n\n"
                f"資料庫處置建議：\n{diagnosis['treatment']}"
            ),
        )
        db.query(models.WebcamAlert).filter(models.WebcamAlert.id == alert_id).update(
            {models.WebcamAlert.email_sent: True}, synchronize_session=False,
        )
        db.commit()
        return True
    except Exception as exc:
        db.rollback()
        print(f"[WEBCAM ALERT EMAIL FAILED]: {exc}")
        return False


def serialize_webcam_alert(alert: models.WebcamAlert) -> dict:
    return {
        "id": alert.id,
        "crop_name": alert.crop.crop_name if alert.crop else None,
        "category": alert.category,
        "status_name": alert.status_name,
        "confidence": alert.confidence,
        "consecutive_matches": alert.consecutive_matches,
        "session_id": alert.session_id,
        "region_id": alert.region_id,
        "requires_review": alert.requires_review,
        "grounding_source": alert.grounding_source,
        "reference_source": alert.reference_source,
        "reference_url": alert.reference_url,
        "reference_record_id": alert.reference_record_id,
        "image_url": build_public_image_url(alert.image_url),
        "email_sent": alert.email_sent,
        "acknowledged_at": alert.acknowledged_at,
        "created_at": alert.created_at,
    }
