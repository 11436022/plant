from fastapi import APIRouter, Depends

from app.db.session import get_db_connection
from app.services.auth import verify_admin
from app.services.files import build_public_image_url

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/all-diaries")
async def admin_get_all_diaries(admin: dict = Depends(verify_admin)):
    """提供管理員檢視全部日誌。"""

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM plant_diary ORDER BY created_at DESC")
            rows = cursor.fetchall()
            for row in rows:
                if row.get("image_url"):
                    row["image_url"] = build_public_image_url(row["image_url"])
            return {"status": "success", "total_records": len(rows), "data": rows}
    finally:
        conn.close()
