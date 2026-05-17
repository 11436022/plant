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
from app.schemas.patch import DiaryUpdate

# 從 prediction 路由器引入暫存區
from app.routers.prediction import prediction_cache

router = APIRouter(prefix="/diaries", tags=["diaries"])





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
        knowledge = await get_or_complete_knowledge(category, new_status, db)
        db_entry.status_name = new_status
        db_entry.suggestion = knowledge["suggestion"]
        db_entry.treatment = knowledge["treatment"]
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
    user_note: str = Body("", embed=True),  # 讓 App 可以選擇性傳入 user_note
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
    #    這裡我們直接使用 create_safe_upload_path 來產生一個新的、安全的正式路徑
    #    這樣可以避免檔案名稱衝突
    formal_path = create_safe_upload_path(temp_path.name)
    shutil.move(str(temp_path), formal_path)

    try:
        # 4. 呼叫既有的 save_to_db 服務，將資料寫入資料庫
        #    注意：這裡我們傳入的是 `formal_path`
        diary_id = await save_to_db(
            data=ai_result,
            image_path=formal_path,  # <-- 將 'file_path' 修正為 'image_path'
            user_id=current_user.user_id,
            user_note=user_note,
            db=db,
        )

        # 5. 從資料庫重新讀取，以回傳完整的資料給 App
        new_diary_entry = (
            db.query(models.PlantDiary)
            .options(joinedload(models.PlantDiary.crop))
            .filter(models.PlantDiary.id == diary_id)
            .first()
        )

        if not new_diary_entry:
            raise HTTPException(status_code=500, detail="Failed to retrieve diary after saving.")

        # 6. 清除快取
        del prediction_cache[prediction_id]

        # 7. 回傳成功的結果
        return {
            "status": "success",
            "message": "Diary created successfully from prediction.",
            "data": {
                "id": new_diary_entry.id,
                "crop_name": new_diary_entry.crop.crop_name if new_diary_entry.crop else "未知作物",
                "status_name": new_diary_entry.status_name,
                "confidence": new_diary_entry.confidence,
                "image_url": build_public_image_url(new_diary_entry.image_url),
                "suggestion": new_diary_entry.suggestion,
                "treatment": new_diary_entry.treatment,
            },
        }
    except Exception as e:
        # 如果儲存過程中發生任何錯誤，最好把移動的檔案移回去，或者記錄下來
        # 這裡我們簡單地回傳錯誤
        # 如果 formal_path 已經存在，可以考慮是否要刪除它
        if formal_path.exists():
            formal_path.unlink()  # 避免留下孤兒檔案
        raise HTTPException(status_code=500, detail=f"Failed to save diary: {str(e)}")