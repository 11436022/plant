import shutil
from pathlib import Path

from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session, joinedload

from app.db import models
from app.core.config import settings
from app.db.session import get_db, get_db_connection
from app.services.ai import ground_diagnosis_in_database, save_to_db
from app.services.auth import get_current_user
from app.services.files import (
    build_public_image_url,
    create_safe_upload_path,
    ensure_image_upload,
)
from app.services.knowledge import get_or_complete_knowledge
from app.schemas.patch import DiaryUpdate, DiaryConfirm, DiaryNoteUpdate

# 從 prediction 路由器引入暫存區
from app.routers.prediction import get_owned_prediction, prediction_cache

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
                COALESCE(c.crop_name, '未知作物') AS crop_name,
                d.status_name,
                d.user_corrected_status,
                d.category, d.confidence, d.requires_review, d.grounding_source,
                d.reference_source, d.reference_url, d.reference_record_id,
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
                row["requires_review"] = bool(row.get("requires_review", True))
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
            SELECT d.*, COALESCE(c.crop_name, '未知作物') AS crop_name, d.user_corrected_status
            FROM plant_diary d
            LEFT JOIN crop c ON d.crop_id = c.crop_id
            WHERE d.id = %s AND d.user_id = %s
            """
            cursor.execute(sql, (diary_id, current_user.user_id))
            detail = cursor.fetchone()
            if not detail:
                raise HTTPException(status_code=404, detail="Diary not found.")
            detail["requires_review"] = bool(detail.get("requires_review", True))
            if detail.get("image_url"):
                detail["image_url"] = build_public_image_url(detail["image_url"])
            return {"status": "success", "data": detail}
    finally:
        conn.close()

@router.patch("/{diary_id}")
async def patch_diary_note(
    diary_id: int,
    update_data: DiaryNoteUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """更新日記的使用者筆記。"""

    user_id = current_user.user_id
    is_admin = current_user.role == "admin"

    db_entry = db.query(models.PlantDiary).filter(models.PlantDiary.id == diary_id).first()
    if not db_entry or (not is_admin and db_entry.user_id != user_id):
        raise HTTPException(status_code=404, detail="Diary not found.")


    if update_data.crop_name or update_data.status_name:
        crop_name = update_data.crop_name or (db_entry.crop.crop_name if db_entry.crop else None)
        crop = db.query(models.Crop).filter(models.Crop.crop_name == crop_name).first()
        if not crop:
            raise HTTPException(status_code=400, detail="Crop must exist in the reference database.")
        status_name = update_data.status_name or db_entry.status_name
        disease = db.query(models.Disease).filter(
            models.Disease.crop_id == crop.crop_id, models.Disease.disease_name == status_name,
        ).first()
        pest = db.query(models.Pest).filter(
            models.Pest.crop_id == crop.crop_id, models.Pest.pest_name == status_name,
        ).first()
        category = "disease" if disease else "pest" if pest else "healthy" if status_name == "健康" else "unknown"
        if category == "unknown":
            raise HTTPException(status_code=400, detail="Status must match the selected crop; use user_corrected_status for a personal annotation.")
        grounded = ground_diagnosis_in_database(
            {"crop_name": crop.crop_name, "category": category, "status_name": status_name, "confidence": 1.0}, db,
        )
        db_entry.crop_id = crop.crop_id
        db_entry.status_name = status_name
        db_entry.category = category
        db_entry.disease_id = disease.disease_id if disease else None
        db_entry.pest_id = pest.pest_id if pest else None
        # A manual edit is not a new model inference or expert review.
        db_entry.confidence = None
        db_entry.requires_review = True
        db_entry.grounding_source = "user_edited_database_match"
        for field in ("reference_source", "reference_url", "reference_record_id"):
            setattr(db_entry, field, grounded.get(field))
        db_entry.gemini_suggestion = grounded["suggestion"]
        db_entry.gemini_treatment = grounded["treatment"]

    optional_fields = ["user_note"]
    for field in optional_fields:
        value = getattr(update_data, field)
        if value is not None:
            setattr(db_entry, field, value)
    
    # 處理使用者修正的狀態
    if update_data.user_corrected_status is not None:
        db_entry.user_corrected_status = update_data.user_corrected_status


    db.commit()
    return {"status": "success", "message": "Diary note updated successfully."}


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
            local_image = Path(image_path).resolve()
            if settings.UPLOAD_DIR.resolve() in local_image.parents and local_image.exists():
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
    cached_data = get_owned_prediction(prediction_id, current_user.user_id)

    ai_result = cached_data["result"]
    temp_path = Path(cached_data["temp_path"])

    # 方案 A 核心防禦：未知作物結果禁止寫入病例日記
    crop_name = ai_result.get("crop_name")
    if crop_name in ["未知作物", "未知", "無法判定", None]:
        raise HTTPException(
            status_code=400,
            detail="診斷結果為未知植物或無法判定之病害，不可存入病歷日記。"
        )

    # 2. 檢查圖片是否存在
    if not temp_path.exists():
        prediction_cache.pop(prediction_id, None)
        raise HTTPException(status_code=404, detail="Temporary image file not found.")

    # 3. 將圖片從臨時資料夾移動到正式的 uploads 資料夾
    formal_path = create_safe_upload_path(temp_path.name)

    # 4. 儲存後端快取中的診斷結果，不使用前端傳回的文字覆蓋作物、病蟲害或建議。
    #    predict API 已在後端完成資料庫清單校驗；confirm 只負責使用者確認與備註。

    get_owned_prediction(prediction_id, current_user.user_id, consume=True)
    diary_id = None
    try:
        shutil.move(str(temp_path), formal_path)
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
        prediction_cache.pop(prediction_id, None)

        # 8. 回傳成功的結果 (使用新的屬性名稱)
        return {
            "status": "success",
            "message": "Diary created successfully from prediction.",
            "data": {
                "id": new_diary_entry.id,
                "crop_name": new_diary_entry.crop.crop_name if new_diary_entry.crop else "未知作物",
                "status_name": new_diary_entry.status_name,
                "confidence": new_diary_entry.confidence,
                "category": new_diary_entry.category,
                "requires_review": new_diary_entry.requires_review,
                "grounding_source": new_diary_entry.grounding_source,
                "reference_source": new_diary_entry.reference_source,
                "reference_url": new_diary_entry.reference_url,
                "reference_record_id": new_diary_entry.reference_record_id,
                "image_url": build_public_image_url(new_diary_entry.image_url),
                "suggestion": new_diary_entry.gemini_suggestion, # <-- 使用新的屬性名
                "treatment": new_diary_entry.gemini_treatment,   # <-- 使用新的屬性名
            },
        }
    except Exception as e:
        db.rollback()
        if diary_id is None:
            if formal_path.exists():
                shutil.move(str(formal_path), temp_path)
            prediction_cache[prediction_id] = cached_data
        raise HTTPException(status_code=500, detail="Failed to save diary.") from e
