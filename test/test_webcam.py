import io
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi import HTTPException
from PIL import Image, ImageDraw


ROOT_DIR = Path(__file__).parent.parent
sys.path.append(str(ROOT_DIR))

os.environ.setdefault("DB_USER", "test")
os.environ.setdefault("DB_PASSWORD", "test")
os.environ.setdefault("DB_HOST", "127.0.0.1")
os.environ.setdefault("DB_NAME", "plant_test")

from app.core.config import settings
from app.services.webcam import AlertConsensusTracker, validate_webcam_frame


def _jpeg_bytes(size=(640, 480), patterned=True) -> bytes:
    image = Image.new("RGB", size, "#7aa36b" if patterned else "#808080")
    if patterned:
        draw = ImageDraw.Draw(image)
        for offset in range(0, max(size), 40):
            draw.line((offset, 0, 0, offset), fill="#203b2a", width=8)
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=85)
    return buffer.getvalue()


def _grounded_diagnosis(status_name="晚疫病") -> dict:
    return {
        "crop_name": "番茄",
        "category": "disease",
        "status_name": status_name,
        "confidence": 0.91,
        "grounding_source": "disease_database",
        "requires_review": False,
    }


def test_validate_webcam_frame_accepts_detailed_jpeg(monkeypatch):
    monkeypatch.setattr(settings, "WEBCAM_MAX_IMAGE_BYTES", 8 * 1024 * 1024)
    monkeypatch.setattr(settings, "WEBCAM_MIN_IMAGE_WIDTH", 320)
    monkeypatch.setattr(settings, "WEBCAM_MIN_IMAGE_HEIGHT", 240)

    metadata = validate_webcam_frame(_jpeg_bytes(), "image/jpeg")

    assert metadata.width == 640
    assert metadata.height == 480
    assert metadata.image_format == "JPEG"


def test_validate_webcam_frame_rejects_blank_image(monkeypatch):
    monkeypatch.setattr(settings, "WEBCAM_MIN_IMAGE_WIDTH", 320)
    monkeypatch.setattr(settings, "WEBCAM_MIN_IMAGE_HEIGHT", 240)

    with pytest.raises(HTTPException) as error:
        validate_webcam_frame(_jpeg_bytes(patterned=False), "image/jpeg")

    assert error.value.status_code == 422


def test_validate_webcam_frame_rejects_small_image(monkeypatch):
    monkeypatch.setattr(settings, "WEBCAM_MIN_IMAGE_WIDTH", 320)
    monkeypatch.setattr(settings, "WEBCAM_MIN_IMAGE_HEIGHT", 240)

    with pytest.raises(HTTPException) as error:
        validate_webcam_frame(_jpeg_bytes(size=(160, 120)), "image/jpeg")

    assert error.value.status_code == 400


def test_consensus_requires_three_matching_grounded_diagnoses(monkeypatch):
    monkeypatch.setattr(settings, "WEBCAM_ALERT_CONFIDENCE", 0.8)
    monkeypatch.setattr(settings, "WEBCAM_ALERT_CONSECUTIVE_MATCHES", 3)
    monkeypatch.setattr(settings, "WEBCAM_ALERT_COOLDOWN_SECONDS", 60)
    tracker = AlertConsensusTracker()
    diagnosis = _grounded_diagnosis()
    now = datetime(2026, 7, 20, tzinfo=timezone.utc)

    assert tracker.evaluate(7, diagnosis, now)["streak"] == 1
    assert tracker.evaluate(7, diagnosis, now)["triggered"] is False
    assert tracker.evaluate(7, diagnosis, now)["triggered"] is True
    assert tracker.evaluate(7, diagnosis, now)["reason"] == "cooldown"


def test_consensus_resets_after_unknown_frame(monkeypatch):
    monkeypatch.setattr(settings, "WEBCAM_ALERT_CONFIDENCE", 0.8)
    monkeypatch.setattr(settings, "WEBCAM_ALERT_CONSECUTIVE_MATCHES", 3)
    tracker = AlertConsensusTracker()
    diagnosis = _grounded_diagnosis()

    tracker.evaluate(11, diagnosis)
    reset = tracker.evaluate(
        11,
        {
            "category": "unknown",
            "confidence": 0.5,
            "grounding_source": "safety_fallback",
            "requires_review": True,
        },
    )

    assert reset["streak"] == 0
    assert tracker.evaluate(11, diagnosis)["streak"] == 1


def test_consensus_can_alert_again_after_cooldown(monkeypatch):
    monkeypatch.setattr(settings, "WEBCAM_ALERT_CONFIDENCE", 0.8)
    monkeypatch.setattr(settings, "WEBCAM_ALERT_CONSECUTIVE_MATCHES", 3)
    monkeypatch.setattr(settings, "WEBCAM_ALERT_COOLDOWN_SECONDS", 60)
    tracker = AlertConsensusTracker()
    diagnosis = _grounded_diagnosis()
    first_scan = datetime(2026, 7, 20, tzinfo=timezone.utc)

    tracker.evaluate(17, diagnosis, first_scan)
    tracker.evaluate(17, diagnosis, first_scan)
    assert tracker.evaluate(17, diagnosis, first_scan)["triggered"] is True

    after_cooldown = first_scan + timedelta(seconds=61)
    assert tracker.evaluate(17, diagnosis, after_cooldown)["triggered"] is True
