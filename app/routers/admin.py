import os
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
import pymysql

from app.db.session import get_db_connection
from app.services.files import build_public_image_url

router = APIRouter(prefix="/admin", tags=["admin"])

@router.get("/", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    """管理者後台首頁 - 顯示診斷紀錄表格"""
    conn = get_db_connection()
    try:
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute("SELECT * FROM plant_diary ORDER BY created_at DESC")
            rows = cursor.fetchall()
            
            for row in rows:
                if row.get("image_url"):
                    # 擷取純檔名 (例如從 C:\...\123.jpg 變成 123.jpg)
                    filename = os.path.basename(row["image_url"])
                    # 強制轉換成網頁能讀取的相對路徑
                    row["image_url"] = f"/static/uploads/{filename}"
            
            # 渲染網頁
            templates_engine = request.app.state.templates
            template = templates_engine.get_template("dashboard.html")
            content = template.render({
                "request": request,
                "title": "植物神醫 - 管理者後台",
                "diaries": rows
            })
            
            return HTMLResponse(content=content)
    finally:
        conn.close()

@router.get("/all-diaries")
async def admin_get_all_diaries():
    """提供管理者檢視全部日誌的 JSON API"""
    conn = get_db_connection()
    try:
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute("SELECT * FROM plant_diary ORDER BY created_at DESC")
            rows = cursor.fetchall()
            for row in rows:
                if row.get("image_url"):
                    # API 保持原本邏輯，或根據需要也套用 basename
                    row["image_url"] = build_public_image_url(row["image_url"])
            return {"status": "success", "total_records": len(rows), "data": rows}
    finally:
        conn.close()