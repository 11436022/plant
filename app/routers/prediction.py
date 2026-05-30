import shutil
import time
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.prediction import PredictionResponse
from app.services.ai import diagnostic_plant, get_reference_lists

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
    try:
        # 1. 產生一個安全的、唯一的檔名，並儲存到臨時位置
        suffix = Path(file.filename).suffix if file.filename else ".jpg"
        safe_filename = f"{uuid.uuid4()}{suffix}"
        temp_file_path = TEMP_DIR / safe_filename
        
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # 2. 呼叫 AI 進行診斷
        crops, diseases, pests = get_reference_lists(db)
        ai_result = diagnostic_plant(str(temp_file_path), crops, diseases, pests)

        if not ai_result:
            raise HTTPException(status_code=502, detail="AI analysis service failed.")

        # 3. 產生唯一的 ID
        prediction_id = str(uuid.uuid4())

        # 4. 將完整的 AI 結果和臨時路徑存入暫存區
        prediction_cache[prediction_id] = {
            "result": ai_result,
            "temp_path": str(temp_file_path)
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

    except Exception as e:
        # 捕捉所有可能的錯誤
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")
    finally:
        # 暫存的圖片不由 predict API 刪除，而是由 confirm API 或過期機制處理
        pass