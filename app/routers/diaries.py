import shutil
from pathlib import Path

from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session, joinedload

from app.db import models
from app.db.session import get_db, get_db_connection
from app.services.ai import classify_agriculture_term, diagnostic_plant, get_reference_lists, save_to_db
from app.services.auth import get_current_user
from app.services.files import (
    build_public_image_url,
    create_safe_upload_path,
    ensure_image_upload,
)
from app.services.knowledge import get_or_complete_knowledge
from app.schemas.patch import DiaryUpdate, DiaryConfirm

# 從 prediction 路由器引入暫存區
from app.routers.prediction import prediction_cache

router = APIRouter(tags=["diaries"])





@router.get("")
async def get_all_history(current_user: models.User = Depends(get_current_user)):
    """取得目前登入者的日誌列表。"""

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
            SELECT
                d.id,
                c.crop_name AS crop_name,
                d.status_name,
                d.user_corrected_status,
                d.image_url,
                d.created_at
            FROM plant_diary d
            LEFT JOIN crop c ON d.crop_id = c.crop_id
            WHERE d.user_id = %s
            ORDER BY d.created_at DESC
            """
            cursor.execute(sql, (current_user.user_id,))
            rows = cursor.fetchall()
            for row in rows:
                if row.get("image_url"):
                    row["image_url"] = build_public_image_url(row["image_url"])
            
            

            return {"status": "success", "count": len(rows), "data": rows}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to fetch diaries: {exc}")
    finally:
        conn.close()


@router.get("/{diary_id}")
async def get_diary_detail(diary_id: int, current_user: models.User = Depends(get_current_user)):
    """取得單筆日誌詳情。"""

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
            SELECT d.*, c.crop_name AS crop_name, d.user_corrected_status
            FROM plant_diary d
            LEFT JOIN crop c ON d.crop_id = c.crop_id
            WHERE d.id = %s AND d.user_id = %s
            """
            cursor.execute(sql, (diary_id, current_user.user_id))
            detail = cursor.fetchone()
            if not detail:
                raise HTTPException(status_code=404, detail="Diary not found.")
            if detail.get("image_url"):
                detail["image_url"] = build_public_image_url(detail["image_url"])
            return {"status": "success", "data": detail}
    finally:
        conn.close()


@router.patch("/{diary_id}")
async def patch_diary(
    diary_id: int,
    update_data: DiaryUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """更新日誌內容。"""

    user_id = current_user.user_id
    is_admin = current_user.role == "admin"

    db_entry = db.query(models.PlantDiary).filter(models.PlantDiary.id == diary_id).first()
    if not db_entry or (not is_admin and db_entry.user_id != user_id):
        raise HTTPException(status_code=404, detail="Diary not found.")

    new_crop_name = update_data.crop_name
    new_status = update_data.status_name

    if new_crop_name:
        crop_info = await get_or_complete_knowledge("crop", new_crop_name, db)
        db_entry.crop_id = crop_info["id"]

    if new_status and new_status not in ["string", ""] and new_status != db_entry.status_name:
        category = await classify_agriculture_term(new_status)
        if category == "invalid":
            raise HTTPException(status_code=400, detail="Status must be a disease or pest.")

        # 呼叫知識庫服務，主要目的是為了拿到新診斷的 ID，並確保它存在於知識庫中
        knowledge = await get_or_complete_knowledge(category, new_status, db)
        
        # 更新日記的狀態名稱
        db_entry.status_name = new_status
        
        # 根據分類，更新對應的關聯 ID，並清除另一個
        if category == "disease":
            db_entry.disease_id = knowledge["id"]
            db_entry.pest_id = None
        elif category == "pest":
            db_entry.pest_id = knowledge["id"]
            db_entry.disease_id = None
        
        # 關鍵：不再用知識庫的通用 description 和 treatment 覆蓋 AI 的原始分析結果
        # db_entry.suggestion = knowledge["suggestion"]
        # db_entry.treatment = knowledge["treatment"]

    optional_fields = ["user_note"]
    for field in optional_fields:
        value = getattr(update_data, field)
        if value is not None:
            setattr(db_entry, field, value)
    
    # 處理使用者修正的狀態
    if update_data.user_corrected_status is not None:
        db_entry.user_corrected_status = update_data.user_corrected_status

    db.commit()
    return {"status": "success", "message": "Diary updated successfully."}


@router.delete("/{diary_id}")
async def delete_diary(diary_id: int, current_user: models.User = Depends(get_current_user)):
    """刪除目前使用者自己的日誌與圖片。"""

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT image_url FROM plant_diary WHERE id = %s AND user_id = %s",
                (diary_id, current_user.user_id),
            )
            record = cursor.fetchone()
            if not record:
                raise HTTPException(status_code=404, detail="Diary not found.")
            cursor.execute(
                "DELETE FROM plant_diary WHERE id = %s AND user_id = %s",
                (diary_id, current_user.user_id),
            )
            conn.commit()

        image_path = record.get("image_url")
        if image_path:
            local_image = Path(image_path)
            if local_image.exists():
                local_image.unlink()

        return {"status": "success", "message": f"Diary {diary_id} deleted."}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to delete diary: {exc}")
    finally:
        conn.close()


@router.post("/confirm/{prediction_id}", status_code=201)
async def confirm_and_create_diary(
    prediction_id: str,
    payload: DiaryConfirm,  # <-- 使用新的 Pydantic 模型
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    從暫存區確認分析結果，並正式建立一筆日誌。
    """
    # 1. 從快取中查找預測結果
    cached_data = prediction_cache.get(prediction_id)
    if not cached_data:
        raise HTTPException(status_code=404, detail="Prediction ID not found or has expired.")

    ai_result = cached_data["result"]
    temp_path = Path(cached_data["temp_path"])

    # 2. 檢查圖片是否存在
    if not temp_path.exists():
        raise HTTPException(status_code=404, detail="Temporary image file not found.")

    # 3. 將圖片從臨時資料夾移動到正式的 uploads 資料夾
    formal_path = create_safe_upload_path(temp_path.name)
    shutil.move(str(temp_path), formal_path)

    # ================= 核心修改 =================
    # 4. 直接使用前端傳來的資料，不再進行複雜的字串拆分解析
    try:
        ai_result["status_name"] = payload.disease_name.replace("診斷：", "").strip()
        ai_result["suggestion"] = payload.gemini_advice
        ai_result["treatment"] = "" # 或是從 advice 中嘗試拆分，但失敗也不要崩潰

        if "【治療方法】" in payload.gemini_advice:
            parts = payload.gemini_advice.split("【治療方法】")
            ai_result["suggestion"] = parts[0].replace("【專家建議】", "").strip()
            ai_result["treatment"] = parts[1].strip()
    except Exception as e:
        print(f"解析建議文字出錯，將儲存原始文字: {e}")
        ai_result["suggestion"] = payload.gemini_advice
        ai_result["treatment"] = ""


    try:
        # 5. 呼叫既有的 save_to_db 服務，將資料寫入資料庫
        diary_id = await save_to_db(
            data=ai_result,
            image_path=formal_path,
            user_id=current_user.user_id,
            user_note=payload.user_note, # <-- 使用 payload 中的 user_note
            db=db,
        )

        # 6. 從資料庫重新讀取，以回傳完整的資料給 App
        new_diary_entry = (
            db.query(models.PlantDiary)
            .options(joinedload(models.PlantDiary.crop))
            .filter(models.PlantDiary.id == diary_id)
            .first()
        )

        if not new_diary_entry:
            raise HTTPException(status_code=500, detail="Failed to retrieve diary after saving.")

        # 7. 清除快取
        del prediction_cache[prediction_id]

        # 8. 回傳成功的結果 (使用新的屬性名稱)
        return {
            "status": "success",
            "message": "Diary created successfully from prediction.",
            "data": {
                "id": new_diary_entry.id,
                "crop_name": new_diary_entry.crop.crop_name if new_diary_entry.crop else "未知作物",
                "status_name": new_diary_entry.status_name,
                "confidence": new_diary_entry.confidence,
                "image_url": build_public_image_url(new_diary_entry.image_url),
                "suggestion": new_diary_entry.gemini_suggestion, # <-- 使用新的屬性名
                "treatment": new_diary_entry.gemini_treatment,   # <-- 使用新的屬性名
            },
        }
    except Exception as e:
        if formal_path.exists():
            formal_path.unlink()
        raise HTTPException(status_code=500, detail=f"Failed to save diary: {str(e)}")