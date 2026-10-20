from fastapi import APIRouter, Depends,HTTPException
from sqlalchemy.orm import Session

from app.db import models
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


@router.get("/crops", status_code=200)
async def get_all_crops(db: Session = Depends(get_db)):
    """
    獲取資料庫中所有作物的完整參考列表，供使用者拍照前或 Webcam 執行前下拉選取。
    第一項固定為「未知」，隨後包含資料庫與主動學習記憶庫中全部作物名稱。
    支援【主動學習自動登錄】：任何經專家校正之新作物，均會自動登錄並出現在下拉選單中。
    """
    try:
        crop_records = (
            db.query(models.Crop.crop_name)
            .filter(models.Crop.crop_name.isnot(None), models.Crop.crop_name != "")
            .distinct()
            .all()
        )
        crop_set = {c[0].strip() for c in crop_records if c[0] and c[0].strip()}

        # 動態補足主動學習與視覺特徵記憶庫中專家覆核之作物
        from app.services.visual_memory import visual_memory, is_valid_crop_name
        from app.services.knowledge import ensure_crop_exists_in_db

        vm_crops = {r["crop_name"].strip() for r in visual_memory.records if is_valid_crop_name(r.get("crop_name"))}
        for vmc in vm_crops:
            if vmc not in crop_set:
                ensure_crop_exists_in_db(vmc, db=db)
                crop_set.add(vmc)

        db_crops = sorted(list(crop_set))
        if "未知" in db_crops:
            db_crops.remove("未知")

        full_crops = ["未知"] + db_crops
        return {
            "status": "success",
            "count": len(full_crops),
            "data": full_crops,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch crops: {str(e)}")