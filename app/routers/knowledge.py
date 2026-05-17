from fastapi import APIRouter, Depends,HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.ai import get_reference_lists

router = APIRouter(
    prefix="/knowledge",
    tags=["knowledge"]
)

@router.get("/diagnoses", status_code=200)
async def get_all_diagnoses(db: Session = Depends(get_db)):
    """
    獲取所有可用的「病害」與「蟲害」參考列表。

    這個 API 會從資料庫中讀取 `diseases` 和 `pests` 這兩個知識庫，
    並將它們合併成一個單一的列表回傳。
    這主要用於前端，讓使用者在回報 AI 診斷錯誤時，有一個可供選擇的列表。
    """
    try:
        # 1. 呼叫核心服務，從資料庫獲取原始數據
        _crops, diseases, pests = get_reference_lists(db)

        # 2. 組合與格式化回傳的資料
        # 我們將 'diseases' 和 'pests' 兩個列表合併
        
        combined_list = [
            {"name": item, "category": "disease"} for item in diseases
        ] + [
            {"name": item, "category": "pest"} for item in pests
        ]
        
        # 根據名稱排序，讓前端的列表更有序
        sorted_list = sorted(combined_list, key=lambda x: x['name'])

        return {
            "status": "success",
            "count": len(sorted_list),
            "data": sorted_list
        }
    except Exception as e:
        # 捕捉所有可能的錯誤
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")