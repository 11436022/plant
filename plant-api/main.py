from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from schemas import PredictionResponse
import time

app = FastAPI(title="Plant Identification API")

# 解決跨域問題 (讓前端能訪問)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/v1/predict", response_model=PredictionResponse)
async def predict_plant(file: UploadFile = File(...)):
    # 1. 驗證文件格式
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="文件格式錯誤，請上傳圖片")

    # 2. 模擬處理時間 (實際開發時這裡會呼叫你的模型)
    start_time = time.time()
    
    # 這裡預留給你的預測邏輯 (Mock Data)
    mock_result = {
        "plant_name": "龜背芋 (Monstera deliciosa)",
        "confidence": 0.952,
        "is_healthy": True
    }
    
    process_time = time.time() - start_time

    # 3. 回傳標準化格式
    return {
        "status": "success",
        "data": mock_result,
        "metadata": {
            "filename": file.filename,
            "process_time": f"{process_time:.4f}s"
        }
    }