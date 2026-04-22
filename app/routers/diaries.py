import shutil
from pathlib import Path

from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.db import models
from app.db.session import get_db, get_db_connection
from app.services.ai import classify_agriculture_term, diagnostic_plant, get_reference_lists, save_to_db
from app.services.auth import get_current_user
from app.services.files import build_public_image_url, create_safe_upload_path, ensure_image_upload
from app.services.knowledge import get_or_complete_knowledge

router = APIRouter(prefix="/diaries", tags=["diaries"])


@router.post("/upload")
async def create_diary(
    user_note: str = Form(""),
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """上傳圖片、完成診斷並寫入日誌。"""

    ensure_image_upload(file)
    file_path = create_safe_upload_path(file.filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        crops, diseases, pests = get_reference_lists(db)
        result = diagnostic_plant(file_path.as_posix(), crops, diseases, pests)
        if not result:
            raise HTTPException(status_code=500, detail="AI diagnosis failed.")

        confidence = float(result.get("confidence", 0.0) or 0.0)
        if confidence < 0.6:
            raise HTTPException(status_code=422, detail="Image confidence is too low.")

        diary_id = await save_to_db(result, file_path, current_user["user_id"], user_note, db)
        return {
            "status": "success",
            "message": "Diary created successfully.",
            "data": {
                "diary_id": diary_id,
                "user": current_user["user_id"],
                "category": result.get("category"),
                "status_name": result.get("status_name"),
                "confidence": confidence,
                "image_url": build_public_image_url(file_path.as_posix()),
                "suggestion": result.get("suggestion"),
                "treatment": result.get("treatment"),
            },
        }
    except Exception:
        if file_path.exists():
            file_path.unlink()
        raise


@router.get("")
async def get_all_history(current_user: dict = Depends(get_current_user)):
    """取得目前登入者的日誌列表。"""

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
            SELECT
                d.id,
                c.crop_name AS crop_name,
                d.status_name,
                d.image_url,
                d.created_at
            FROM plant_diary d
            LEFT JOIN crop c ON d.crop_id = c.crop_id
            WHERE d.user_id = %s
            ORDER BY d.created_at DESC
            """
            cursor.execute(sql, (current_user["user_id"],))
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
async def get_diary_detail(diary_id: int, current_user: dict = Depends(get_current_user)):
    """取得單筆日誌詳情。"""

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
            SELECT d.*, c.crop_name AS crop_name
            FROM plant_diary d
            LEFT JOIN crop c ON d.crop_id = c.crop_id
            WHERE d.id = %s AND d.user_id = %s
            """
            cursor.execute(sql, (diary_id, current_user["user_id"]))
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
    update_data: dict = Body(...),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """更新日誌內容。"""

    user_id = current_user["user_id"]
    is_admin = current_user.get("role") == "admin"

    db_entry = db.query(models.PlantDiary).filter(models.PlantDiary.id == diary_id).first()
    if not db_entry or (not is_admin and db_entry.user_id != user_id):
        raise HTTPException(status_code=404, detail="Diary not found.")

    new_crop_name = update_data.get("crop_name")
    new_status = update_data.get("status_name")

    if new_crop_name:
        crop_info = await get_or_complete_knowledge("crop", new_crop_name, db)
        db_entry.crop_id = crop_info["id"]

    if new_status:
        category = await classify_agriculture_term(new_status)
        if category == "invalid":
            raise HTTPException(status_code=400, detail="Status must be a disease or pest.")
        knowledge = await get_or_complete_knowledge(category, new_status, db)
        db_entry.status_name = new_status
        db_entry.suggestion = knowledge["suggestion"]
        db_entry.treatment = knowledge["treatment"]

    if "user_note" in update_data:
        db_entry.user_note = update_data["user_note"]
    if "suggestion" in update_data:
        db_entry.suggestion = update_data["suggestion"]
    if "treatment" in update_data:
        db_entry.treatment = update_data["treatment"]

    db.commit()
    return {"status": "success", "message": "Diary updated successfully."}


@router.delete("/{diary_id}")
async def delete_diary(diary_id: int, current_user: dict = Depends(get_current_user)):
    """刪除目前使用者自己的日誌與圖片。"""

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT image_url FROM plant_diary WHERE id = %s AND user_id = %s",
                (diary_id, current_user["user_id"]),
            )
            record = cursor.fetchone()
            if not record:
                raise HTTPException(status_code=404, detail="Diary not found.")
            cursor.execute(
                "DELETE FROM plant_diary WHERE id = %s AND user_id = %s",
                (diary_id, current_user["user_id"]),
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
