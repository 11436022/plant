import os
from fastapi import APIRouter, Request, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse
import pymysql

from app.db.session import get_db_connection
from app.services.files import build_public_image_url

router = APIRouter(prefix="/admin", tags=["admin"])

ITEMS_PER_PAGE = 20  # 每頁顯示的紀錄數量

@router.get("/", response_class=HTMLResponse)
async def admin_dashboard(request: Request, search: str = None, page: int = Query(1, ge=1)):
    """【查詢】功能：支援模糊搜尋、分頁，並顯示所有紀錄與統計數據"""
    conn = get_db_connection()
    try:
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            
            # 1. 數據總覽儀表板
            cursor.execute("SELECT COUNT(*) as count FROM user")
            total_users = cursor.fetchone()['count']
            
            cursor.execute("SELECT COUNT(*) as count FROM plant_diary")
            total_diaries = cursor.fetchone()['count']
            
            cursor.execute("SELECT COUNT(DISTINCT status_name) as count FROM plant_diary WHERE status_name IS NOT NULL AND status_name != ''")
            total_diseases = cursor.fetchone()['count']
            
            cursor.execute("SELECT COUNT(*) as count FROM plant_diary WHERE DATE(created_at) = CURDATE()")
            today_diaries = cursor.fetchone()['count']

            # 2. 關聯使用者 & 3. AI vs. 使用者修正 & 5. 分頁
            base_sql = "FROM plant_diary d LEFT JOIN user u ON d.user_id = u.user_id"
            where_clause = ""
            params = []
            if search:
                # 讓搜尋功能也支援搜尋使用者名稱
                where_clause = "WHERE d.status_name LIKE %s OR u.username LIKE %s"
                params.extend([f"%{search}%", f"%{search}%"])

            # 取得篩選後的總筆數，用於計算分頁
            count_sql = f"SELECT COUNT(d.id) as count {base_sql} {where_clause}"
            cursor.execute(count_sql, tuple(params))
            total_items = cursor.fetchone()['count']
            total_pages = (total_items + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE

            # 取得當前頁面的資料
            offset = (page - 1) * ITEMS_PER_PAGE
            main_sql = f"""
                SELECT 
                    d.id, d.status_name, d.user_corrected_status, d.image_url, d.created_at,
                    u.username
                {base_sql} {where_clause}
                ORDER BY d.created_at DESC
                LIMIT %s OFFSET %s
            """
            paged_params = tuple(params + [ITEMS_PER_PAGE, offset])
            cursor.execute(main_sql, paged_params)
            rows = cursor.fetchall()
            
            # 4. 圖片縮圖顯示 (URL 處理)
            for row in rows:
                if row.get("image_url"):
                    row["image_url"] = build_public_image_url(row["image_url"])

            templates_engine = request.app.state.templates
            template = templates_engine.get_template("dashboard.html")
            content = template.render({
                "request": request,
                "title": "植物神醫 - 管理者後台",
                "diaries": rows,
                "search_query": search or "",
                # 傳遞新的統計數據到模板
                "summary": {
                    "total_users": total_users,
                    "total_diaries": total_diaries,
                    "total_diseases": total_diseases,
                    "today_diaries": today_diaries,
                },
                # 傳遞分頁相關資訊到模板
                "pagination": {
                    "current_page": page,
                    "total_pages": total_pages,
                    "total_items": total_items,
                    "base_url": str(request.url_for("admin_dashboard")), # 讓模板可以產生分頁連結
                }
            })
            
            return HTMLResponse(content=content)
    finally:
        conn.close()


@router.post("/feedback/annotate/{feedback_id}", response_class=RedirectResponse)
async def admin_feedback_annotate(
    request: Request,
    feedback_id: int,
    plant_name: str = Form(None),
    disease_name: str = Form(None)
):
    """【更新】功能：儲存管理者對使用者回饋的標註"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
                UPDATE diagnosis_feedback
                SET manager_corrected_plant_name = %s,
                    manager_corrected_disease_name = %s
                WHERE id = %s
            """
            # 如果表單欄位是空的，會收到空字串，將其轉為 None 存入資料庫
            cursor.execute(sql, (plant_name or None, disease_name or None, feedback_id))
        conn.commit()
    finally:
        conn.close()

    # 操作完成後，重定向回使用者回饋列表頁面，以查看更新結果
    # 使用 303 See Other 狀態碼是 POST-Redirect-GET 模式的標準做法
    return RedirectResponse(url=request.url_for("admin_feedback_list"), status_code=303)

@router.get("/feedback/", response_class=HTMLResponse)
async def admin_feedback_list(request: Request, page: int = Query(1, ge=1)):
    """【查詢】功能：顯示、搜尋和分頁所有使用者回饋"""
    conn = get_db_connection()
    try:
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            # 取得總筆數，用於計算分頁
            cursor.execute("SELECT COUNT(id) as count FROM diagnosis_feedback")
            total_items = cursor.fetchone()['count']
            total_pages = (total_items + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE

            # 取得當前頁面的資料
            offset = (page - 1) * ITEMS_PER_PAGE
            sql = """
                SELECT 
                    f.id, f.image_url, f.original_plant_name, f.original_disease_name, 
                    f.is_plant_error, f.is_disease_error, f.corrected_plant_name, 
                    f.corrected_disease_name, f.created_at,
                    f.manager_corrected_plant_name, f.manager_corrected_disease_name,
                    u.username
                FROM diagnosis_feedback f
                LEFT JOIN user u ON f.user_id = u.user_id
                ORDER BY f.created_at DESC
                LIMIT %s OFFSET %s
            """
            cursor.execute(sql, (ITEMS_PER_PAGE, offset))
            feedbacks = cursor.fetchall()

            # 將圖片路徑轉換為可公開存取的 URL
            for feedback in feedbacks:
                if feedback.get("image_url"):
                    feedback["image_url"] = build_public_image_url(feedback["image_url"])

            templates_engine = request.app.state.templates
            template = templates_engine.get_template("feedback.html")
            content = template.render({
                "request": request,
                "title": "使用者回饋 - 管理者後台",
                "feedbacks": feedbacks,
                "pagination": {
                    "current_page": page,
                    "total_pages": total_pages,
                    "total_items": total_items,
                    "base_url": str(request.url_for("admin_feedback_list")),
                }
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

@router.get("/users/", response_class=HTMLResponse)
async def admin_users_list(request: Request, search: str = None, page: int = Query(1, ge=1)):
    """【查詢】功能：顯示、搜尋和分頁所有使用者"""
    conn = get_db_connection()
    try:
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            base_sql = "FROM user"
            where_clause = ""
            params = []
            if search:
                where_clause = "WHERE username LIKE %s OR email LIKE %s"
                params.extend([f"%{search}%", f"%{search}%"])

            # 取得篩選後的總筆數，用於計算分頁
            count_sql = f"SELECT COUNT(user_id) as count {base_sql} {where_clause}"
            cursor.execute(count_sql, tuple(params))
            total_items = cursor.fetchone()['count']
            total_pages = (total_items + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE

            # 取得當前頁面的資料
            offset = (page - 1) * ITEMS_PER_PAGE
            main_sql = f"""
                SELECT 
                    user_id, username, email, full_name, created_at, is_email_verified, email_verified_at
                {base_sql} {where_clause}
                ORDER BY user_id 
                LIMIT %s OFFSET %s
            """
            paged_params = tuple(params + [ITEMS_PER_PAGE, offset])
            cursor.execute(main_sql, paged_params)
            users = cursor.fetchall()

            templates_engine = request.app.state.templates
            template = templates_engine.get_template("users.html")
            content = template.render({
                "request": request,
                "title": "使用者管理 - 管理者後台",
                "users": users,
                "search_query": search or "",
                "pagination": {
                    "current_page": page,
                    "total_pages": total_pages,
                    "total_items": total_items,
                    "base_url": str(request.url_for("admin_users_list")),
                }
            })
            
            return HTMLResponse(content=content)
    finally:
        conn.close()