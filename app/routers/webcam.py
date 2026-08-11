from datetime import datetime, timezone
from pathlib import Path
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.db import models
from app.db.session import get_db
from app.services.ai import diagnostic_plant, get_reference_lists, ground_diagnosis_in_database
from app.services.auth import get_current_user
from app.services.webcam import (
    alert_consensus,
    create_webcam_alert,
    save_alert_image,
    serialize_webcam_alert,
    validate_webcam_frame,
)


router = APIRouter(prefix="/webcam", tags=["webcam"])
page_router = APIRouter(tags=["webcam"])
TEMP_DIR = settings.STATIC_DIR / "tmp" / "webcam"
TEMP_DIR.mkdir(parents=True, exist_ok=True)


@page_router.get("/webcam", response_class=FileResponse, include_in_schema=False)
async def webcam_monitor_page():
    return str(settings.BASE_DIR / "templates" / "webcam.html")


@router.get("/settings")
async def get_webcam_settings(current_user: models.User = Depends(get_current_user)):
    return {
        "sample_interval_seconds": settings.WEBCAM_SAMPLE_INTERVAL_SECONDS,
        "alert_confidence": settings.WEBCAM_ALERT_CONFIDENCE,
        "required_matches": settings.WEBCAM_ALERT_CONSECUTIVE_MATCHES,
        "cooldown_seconds": settings.WEBCAM_ALERT_COOLDOWN_SECONDS,
        "max_image_bytes": settings.WEBCAM_MAX_IMAGE_BYTES,
        "minimum_image_size": {
            "width": settings.WEBCAM_MIN_IMAGE_WIDTH,
            "height": settings.WEBCAM_MIN_IMAGE_HEIGHT,
        },
    }


@router.post("/analyze")
async def analyze_webcam_frame(
    file: UploadFile = File(...),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    content = await file.read(settings.WEBCAM_MAX_IMAGE_BYTES + 1)
    metadata = validate_webcam_frame(content, file.content_type)
    suffix = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp"}[metadata.image_format]
    temp_path = TEMP_DIR / f"{uuid.uuid4().hex}{suffix}"
    temp_path.write_bytes(content)

    saved_alert_path = None
    try:
        crops, diseases, pests = get_reference_lists(db)
        model_result = diagnostic_plant(str(temp_path), crops, diseases, pests)
        if not model_result:
            raise HTTPException(status_code=502, detail="AI analysis service failed.")

        diagnosis = ground_diagnosis_in_database(model_result, db)
        monitoring = alert_consensus.evaluate(current_user.user_id, diagnosis)
        alert_data = None

        if monitoring["triggered"]:
            saved_alert_path = save_alert_image(content, metadata.image_format)
            alert = create_webcam_alert(
                db=db,
                user=current_user,
                diagnosis=diagnosis,
                image_path=saved_alert_path,
                consecutive_matches=monitoring["streak"],
            )
            alert_data = serialize_webcam_alert(alert)

        return {
            "status": "success",
            "diagnosis": diagnosis,
            "monitoring": monitoring,
            "alert": alert_data,
            "frame": {
                "width": metadata.width,
                "height": metadata.height,
                "format": metadata.image_format,
            },
        }
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        if saved_alert_path and saved_alert_path.exists():
            saved_alert_path.unlink()
        raise HTTPException(status_code=500, detail=f"Webcam analysis failed: {exc}") from exc
    finally:
        if temp_path.exists():
            temp_path.unlink()


@router.get("/alerts")
async def list_webcam_alerts(
    limit: int = Query(50, ge=1, le=200),
    unacknowledged_only: bool = False,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = (
        db.query(models.WebcamAlert)
        .options(joinedload(models.WebcamAlert.crop))
        .filter(models.WebcamAlert.user_id == current_user.user_id)
    )
    if unacknowledged_only:
        query = query.filter(models.WebcamAlert.acknowledged_at.is_(None))
    alerts = query.order_by(models.WebcamAlert.created_at.desc()).limit(limit).all()
    return {
        "status": "success",
        "count": len(alerts),
        "data": [serialize_webcam_alert(alert) for alert in alerts],
    }


@router.patch("/alerts/{alert_id}/acknowledge")
async def acknowledge_webcam_alert(
    alert_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    alert = (
        db.query(models.WebcamAlert)
        .filter(
            models.WebcamAlert.id == alert_id,
            models.WebcamAlert.user_id == current_user.user_id,
        )
        .first()
    )
    if not alert:
        raise HTTPException(status_code=404, detail="Webcam alert not found.")
    if alert.acknowledged_at is None:
        alert.acknowledged_at = datetime.now(timezone.utc)
        db.commit()
    return {"status": "success", "message": "Webcam alert acknowledged."}


@router.delete("/alerts/{alert_id}")
async def delete_webcam_alert(
    alert_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    alert = (
        db.query(models.WebcamAlert)
        .filter(
            models.WebcamAlert.id == alert_id,
            models.WebcamAlert.user_id == current_user.user_id,
        )
        .first()
    )
    if not alert:
        raise HTTPException(status_code=404, detail="Webcam alert not found.")

    image_path = Path(alert.image_url).resolve()
    upload_root = settings.UPLOAD_DIR.resolve()
    db.delete(alert)
    db.commit()
    if upload_root in image_path.parents and image_path.exists():
        image_path.unlink()
    return {"status": "success", "message": "Webcam alert deleted."}
