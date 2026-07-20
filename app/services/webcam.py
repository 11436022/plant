from __future__ import annotations

import io
import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from fastapi import HTTPException
from PIL import Image, ImageStat, UnidentifiedImageError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db import models
from app.services.email import send_email
from app.services.files import build_public_image_url, create_safe_upload_path


ALLOWED_IMAGE_FORMATS = {"JPEG", "PNG", "WEBP"}


@dataclass(frozen=True)
class FrameMetadata:
    width: int
    height: int
    image_format: str


def validate_webcam_frame(content: bytes, content_type: str | None) -> FrameMetadata:
    """Reject oversized, malformed, tiny, or effectively blank webcam frames."""

    if content_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise HTTPException(status_code=400, detail="Webcam frame must be JPEG, PNG, or WebP.")
    if not content:
        raise HTTPException(status_code=400, detail="Webcam frame is empty.")
    if len(content) > settings.WEBCAM_MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="Webcam frame exceeds the upload size limit.")

    try:
        with Image.open(io.BytesIO(content)) as image:
            image.verify()
        with Image.open(io.BytesIO(content)) as image:
            width, height = image.size
            image_format = str(image.format or "").upper()
            grayscale = image.convert("L")
            grayscale.thumbnail((320, 320))
            contrast = float(ImageStat.Stat(grayscale).stddev[0])
    except (Image.DecompressionBombError, UnidentifiedImageError, OSError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="Webcam frame is not a valid image.") from exc

    if image_format not in ALLOWED_IMAGE_FORMATS:
        raise HTTPException(status_code=400, detail="Unsupported webcam image format.")
    if width < settings.WEBCAM_MIN_IMAGE_WIDTH or height < settings.WEBCAM_MIN_IMAGE_HEIGHT:
        raise HTTPException(
            status_code=400,
            detail=(
                "Webcam frame is too small. "
                f"Minimum size is {settings.WEBCAM_MIN_IMAGE_WIDTH}x{settings.WEBCAM_MIN_IMAGE_HEIGHT}."
            ),
        )
    if contrast < 5.0:
        raise HTTPException(status_code=422, detail="Webcam frame lacks enough visual detail for diagnosis.")

    return FrameMetadata(width=width, height=height, image_format=image_format)


class AlertConsensusTracker:
    """Require repeated matching diagnoses before allowing an automatic alert."""

    def __init__(self) -> None:
        self._states: dict[int, dict] = {}
        self._lock = threading.Lock()

    def evaluate(self, user_id: int, diagnosis: dict, now: datetime | None = None) -> dict:
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
            state = self._states.setdefault(
                user_id,
                {
                    "fingerprint": None,
                    "streak": 0,
                    "last_alert_fingerprint": None,
                    "last_alert_at": None,
                },
            )

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
) -> models.WebcamAlert:
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
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)

    if user.email:
        try:
            send_email(
                to_email=user.email,
                subject=f"Plant Doctor 警報：{alert.status_name}",
                text_body=(
                    f"Webcam 連續 {consecutive_matches} 次辨識到 {diagnosis['crop_name']} "
                    f"可能有 {alert.status_name}，信心值 {alert.confidence:.0%}。\n\n"
                    f"資料庫處置建議：\n{diagnosis['treatment']}"
                ),
            )
            alert.email_sent = True
            db.commit()
            db.refresh(alert)
        except Exception as exc:
            print(f"[WEBCAM ALERT EMAIL FAILED]: {exc}")

    return alert


def serialize_webcam_alert(alert: models.WebcamAlert) -> dict:
    return {
        "id": alert.id,
        "crop_name": alert.crop.crop_name if alert.crop else None,
        "category": alert.category,
        "status_name": alert.status_name,
        "confidence": alert.confidence,
        "consecutive_matches": alert.consecutive_matches,
        "image_url": build_public_image_url(alert.image_url),
        "email_sent": alert.email_sent,
        "acknowledged_at": alert.acknowledged_at,
        "created_at": alert.created_at,
    }
