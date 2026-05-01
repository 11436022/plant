import os
from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
import pymysql

from app.db.session import get_db_connection
from app.services.files import build_public_image_url

router = APIRouter(prefix="/admin", tags=["admin"])

@router.get("/", response_class=HTMLResponse)
async def admin_dashboard(request: Request, search: str = None):
    """【查詢】功能：支援模糊搜尋病名，並顯示所有紀錄"""
    conn = get_db_connection()
    try:
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            # 如果有搜尋字串，就加入 WHERE 子句
            if search:
                sql = "SELECT * FROM plant_diary WHERE status_name LIKE %s ORDER BY created_at DESC"
                cursor.execute(sql, (f"%{search}%",))
            else:
                sql = "SELECT * FROM plant_diary ORDER BY created_at DESC"
                cursor.execute(sql)
            
            rows = cursor.fetchall()
            
            for row in rows:
                if row.get("image_url"):
                    filename = os.path.basename(row["image_url"])
                    row["image_url"] = f"/static/uploads/{filename}"
            
            templates_engine = request.app.state.templates
            template = templates_engine.get_template("dashboard.html")
            content = template.render({
                "request": request,
                "title": "植物神醫 - 管理者後台",
                "diaries": rows,
                "search_query": search or ""  # 把搜尋詞傳回網頁，讓搜尋框記得剛才搜了什麼
            })
            
            return HTMLResponse(content=content)
    finally:
        conn.close()

@router.post("/add")
async def admin_add_diary(status_name: str = Form(...)):
    """【新增】功能：手動增加一筆紀錄"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            sql = "INSERT INTO plant_diary (status_name, created_at) VALUES (%s, NOW())"
            cursor.execute(sql, (status_name,))
        conn.commit()
        return RedirectResponse(url="/admin/", status_code=303)
    finally:
        conn.close()

@router.post("/update/{diary_id}")
async def admin_update_diary(diary_id: int, status_name: str = Form(...)):
    """【修改】功能：更新特定紀錄的診斷結果"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            sql = "UPDATE plant_diary SET status_name = %s WHERE id = %s"
            cursor.execute(sql, (status_name, diary_id))
        conn.commit()
        return RedirectResponse(url="/admin/", status_code=303)
    finally:
        conn.close()

@router.post("/delete/{diary_id}")
async def admin_delete_diary(diary_id: int):
    """【刪除】功能：移除特定紀錄"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            sql = "DELETE FROM plant_diary WHERE id = %s"
            cursor.execute(sql, (diary_id,))
        conn.commit()
        return RedirectResponse(url="/admin/", status_code=303)
    finally:
        conn.close()

@router.get("/all-diaries")
async def admin_get_all_diaries():
    """保持不變：供測試使用的 JSON API"""
    conn = get_db_connection()
    try:
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute("SELECT * FROM plant_diary ORDER BY created_at DESC")
            rows = cursor.fetchall()
            for row in rows:
                if row.get("image_url"):
                    row["image_url"] = build_public_image_url(row["image_url"])
            return {"status": "success", "total_records": len(rows), "data": rows}
    finally:
        conn.close()