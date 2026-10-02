import time
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.db.models import User
from app.schemas.prediction import PredictionResponse
from app.services.ai import diagnostic_plant, get_reference_lists, ground_diagnosis_in_database
from app.services.auth import get_current_user
from app.services.files import validate_image_content

# 暫存區：使用一個簡單的 Python 字典來模擬 Redis
# 格式: { "prediction_id": { "result": ai_json_result, "temp_path": "path/to/temp/image.jpg" } }
prediction_cache = {}
PREDICTION_TTL_SECONDS = 900
MAX_PENDING_PREDICTIONS = 100

router = APIRouter(
    prefix="/predict",
    tags=["prediction"]
)

# 建立一個臨時資料夾來存放待確認的圖片
TEMP_DIR = Path("static/tmp")
TEMP_DIR.mkdir(parents=True, exist_ok=True)


def prune_expired_predictions():
    now = time.monotonic()
    for prediction_id, entry in list(prediction_cache.items()):
        if entry.get("expires_at", 0) <= now:
            prediction_cache.pop(prediction_id, None)
            path = Path(entry["temp_path"]).resolve()
            if TEMP_DIR.resolve() in path.parents:
                path.unlink(missing_ok=True)


def get_owned_prediction(prediction_id: str, user_id: int, *, consume: bool = False):
    prune_expired_predictions()
    entry = prediction_cache.get(prediction_id)
    if not entry or entry.get("user_id") != user_id:
        raise HTTPException(status_code=404, detail="Prediction ID not found or has expired.")
    if consume:
        prediction_cache.pop(prediction_id)
    return entry


@router.post("/", status_code=200)
async def predict_plant_status(file: UploadFile = File(...), db: Session = Depends(get_db),
                               current_user: User = Depends(get_current_user)):
    """
    接收圖片，執行 AI 分析，並將結果暫存。

    這個端點會：
    1. 儲存上傳的圖片到一個臨時資料夾。
    2. 呼叫 AI 模型進行分析。
    3. 產生一個唯一的 prediction_id。
    4. 將分析結果和圖片路徑暫存起來。
    5. 回傳 prediction_id 和分析結果給客戶端。
    """
    start_time = time.time()
    temp_file_path = None
    try:
        prune_expired_predictions()
        pending = sum(entry.get("user_id") == current_user.user_id for entry in prediction_cache.values())
        if len(prediction_cache) >= MAX_PENDING_PREDICTIONS or pending >= 10:
            raise HTTPException(status_code=429, detail="Too many pending predictions. Confirm or wait for expiry.")
        content = await file.read(settings.WEBCAM_MAX_IMAGE_BYTES + 1)
        metadata = validate_image_content(content, file.content_type)
        suffix = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp"}[metadata.image_format]
        temp_file_path = TEMP_DIR / f"{uuid.uuid4().hex}{suffix}"
        temp_file_path.write_bytes(content)

        # 2. 呼叫 AI 進行診斷
        crops, diseases, pests = get_reference_lists(db)
        ai_result = diagnostic_plant(str(temp_file_path), crops, diseases, pests)

        if not ai_result:
            raise HTTPException(status_code=502, detail="AI analysis service failed.")
        ai_result = ground_diagnosis_in_database(ai_result, db)

        # 3. 產生唯一的 ID
        prediction_id = str(uuid.uuid4())

        # 4. 將完整的 AI 結果和臨時路徑存入暫存區
        prediction_cache[prediction_id] = {
            "result": ai_result,
            "temp_path": str(temp_file_path),
            "user_id": current_user.user_id,
            "expires_at": time.monotonic() + PREDICTION_TTL_SECONDS,
        }
        
        # 5. 組合回傳給 App 的資料
        response_data = {
            "prediction_id": prediction_id,
            "analysis_result": ai_result,
            "metadata": {
                "filename": Path(file.filename or temp_file_path.name).name,
                "process_time": f"{time.time() - start_time:.4f}s",
            }
        }

        return response_data

    except HTTPException:
        if temp_file_path and temp_file_path.exists():
            temp_file_path.unlink()
        raise
    except Exception as e:
        if temp_file_path and temp_file_path.exists():
            temp_file_path.unlink()
        raise HTTPException(status_code=500, detail="Image analysis failed.") from e
    finally:
        await file.close()
