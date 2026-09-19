import time
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.schemas.prediction import PredictionResponse
from app.services.ai import diagnostic_plant, process_and_update_diagnosis
from app.services.files import ensure_image_upload

# 暫存區：使用一個簡單的 Python 字典來模擬 Redis
# 格式: { "prediction_id": { "result": ai_json_result, "temp_path": "path/to/temp/image.jpg" } }
prediction_cache = {}

router = APIRouter(
    prefix="/predict",
    tags=["prediction"]
)

# 建立一個臨時資料夾來存放待確認的圖片
TEMP_DIR = Path("static/tmp")
TEMP_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/", status_code=200)
async def predict_plant_status(file: UploadFile = File(...), db: Session = Depends(get_db)):
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
        # 1. Only accept bounded images and never trust the client filename.
        ensure_image_upload(file)
        suffix = Path(file.filename or "").suffix.lower() or ".jpg"
        temp_file_path = TEMP_DIR / f"{uuid.uuid4().hex}{suffix}"
        total_bytes = 0
        with open(temp_file_path, "wb") as buffer:
            while chunk := file.file.read(1024 * 1024):
                total_bytes += len(chunk)
                if total_bytes > settings.WEBCAM_MAX_IMAGE_BYTES:
                    raise HTTPException(status_code=413, detail="Image exceeds the upload size limit.")
                buffer.write(chunk)

        # 2. 呼叫 AI 進行診斷 (V3.1 新流程)
        # 步驟 1: 取得 AI 原始、未經驗證的診斷結果
        raw_ai_result = diagnostic_plant(str(temp_file_path))

        # --- DEBUG: 印出 AI 原始預測結果 ---
        if raw_ai_result:
            print("="*50)
            print(f"✅ AI Raw Prediction: {raw_ai_result.get('crop_name', 'N/A')} - {raw_ai_result.get('status_name', 'N/A')}")
            print(f"📊 AI Raw Confidence: {raw_ai_result.get('confidence', 0.0):.4f}")
            print("="*50)
        else:
            print("="*50)
            print("⚠️ AI did not return any prediction.")
            print("="*50)
            raise HTTPException(status_code=502, detail="AI analysis service failed to provide a result.")
        # --- END DEBUG ---

        # 步驟 2: 處理原始結果，與資料庫同步並取得最終可信的診斷
        final_diagnosis = process_and_update_diagnosis(raw_ai_result, db)

        # 3. 產生唯一的 ID
        prediction_id = str(uuid.uuid4())

        # 4. 將完整的最終結果和臨時路徑存入暫存區
        prediction_cache[prediction_id] = {
            "result": final_diagnosis,
            "temp_path": str(temp_file_path)
        }
        
        # 5. 組合回傳給 App 的資料
        response_data = {
            "prediction_id": prediction_id,
            "analysis_result": final_diagnosis,
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
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")
    finally:
        # 暫存的圖片不由 predict API 刪除，而是由 confirm API 或過期機制處理
        pass