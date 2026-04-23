import shutil
import time
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.prediction import PredictionResponse
from app.services.ai import diagnostic_plant, get_reference_lists
from app.services.files import create_safe_upload_path, ensure_image_upload

router = APIRouter(tags=["prediction"])


@router.post("/v1/predict", response_model=PredictionResponse)
async def predict_plant(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """執行純預測，不寫入日誌。"""

    ensure_image_upload(file)
    temp_path = create_safe_upload_path(file.filename)
    start_time = time.time()

    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        crops, diseases, pests = get_reference_lists(db)
        result = diagnostic_plant(temp_path.as_posix(), crops, diseases, pests)
        if not result:
            raise HTTPException(status_code=502, detail="Prediction service failed.")

        category = str(result.get("category", "")).lower()
        plant_name = result.get("crop_name") or "unknown"
        confidence = float(result.get("confidence", 0.0) or 0.0)
        return {
            "status": "success",
            "data": {
                "plant_name": plant_name,
                "confidence": confidence,
                "is_healthy": category == "healthy",
            },
            "metadata": {
                "filename": Path(file.filename or temp_path.name).name,
                "process_time": f"{time.time() - start_time:.4f}s",
                "status_name": result.get("status_name"),
                "category": result.get("category"),
            },
        }
    finally:
        if temp_path.exists():
            temp_path.unlink()
