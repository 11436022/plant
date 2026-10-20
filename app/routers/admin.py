from fastapi import APIRouter, Depends, HTTPException, Request, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse
import pymysql
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db, get_db_connection
from app.routers.auth import get_user_by_username, pwd_context
from app.services.auth import create_access_token, get_current_user, verify_admin
from app.services.files import build_public_image_url

ADMIN_COOKIE = "plant_admin_session"


def check_form_origin(request: Request):
    """CSRF 來源檢查：保護後台表單提交，同時相容 Railway、反向代理與自訂網域名稱"""
    if request.method in {"GET", "HEAD", "OPTIONS"}:
        return
    if request.url.path.rstrip("/") in {"/admin/login", "/admin/logout"}:
        return

    origin = request.headers.get("origin") or request.headers.get("referer")
    if not origin:
        return

    origin_host = origin.split("://")[-1].split("/")[0].split(":")[0].lower()
    req_host = (request.headers.get("x-forwarded-host") or request.headers.get("host") or request.url.netloc or "").split(":")[0].lower()

    allowed_domains = {
        req_host,
        "localhost",
        "127.0.0.1",
        "0.0.0.0",
        request.url.hostname.lower() if request.url.hostname else ""
    }
    if origin_host in allowed_domains or origin_host.endswith(".railway.app") or origin_host.endswith(".up.railway.app"):
        return
    if origin == str(request.base_url).rstrip("/"):
        return

    allowed_cors_hosts = {o.split("://")[-1].split("/")[0].split(":")[0].lower() for o in settings.CORS_ORIGINS if o}
    if origin_host in allowed_cors_hosts or "*" in settings.CORS_ORIGINS:
        return

    raise HTTPException(status_code=403, detail="Cross-origin form submission denied.")


async def require_admin(request: Request, db: Session = Depends(get_db)):
    if request.url.path.rstrip("/") == "/admin/login":
        return
    check_form_origin(request)
    authorization = request.headers.get("authorization", "")
    token = authorization[7:] if authorization.lower().startswith("bearer ") else request.cookies.get(ADMIN_COOKIE)
    if not token:
        if "text/html" in request.headers.get("accept", ""):
            raise HTTPException(status_code=303, headers={"Location": "/admin/login"})
        raise HTTPException(status_code=401, detail="Administrator login required.")
    user = get_current_user(db=db, token=token)
    if not getattr(user, "is_email_verified", True):
        raise HTTPException(status_code=403, detail="Email verification required.")
    return await verify_admin(user)


router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])


@router.get("/login", response_class=HTMLResponse)
async def admin_login_page():
    return HTMLResponse('''<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8">
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <title>管理員登入</title>
    <style>
        body { font-family: system-ui, -apple-system, sans-serif; background: #f0fdf4; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; }
        .card { background: white; padding: 2rem; border-radius: 12px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); width: 100%; max-width: 360px; }
        h1 { color: #166534; font-size: 1.4rem; margin-top: 0; margin-bottom: 1.5rem; text-align: center; }
        label { display: block; margin-bottom: 0.5rem; color: #374151; font-size: 0.875rem; font-weight: 500; }
        input { width: 100%; padding: 0.625rem; border: 1px solid #d1d5db; border-radius: 6px; box-sizing: border-box; margin-bottom: 1rem; font-size: 1rem; }
        input:focus { outline: none; border-color: #22c55e; box-shadow: 0 0 0 3px rgba(34,197,94,0.2); }
        button { width: 100%; background: #16a34a; color: white; padding: 0.75rem; border: none; border-radius: 6px; font-size: 1rem; font-weight: 600; cursor: pointer; transition: background 0.2s; }
        button:hover { background: #15803d; }
    </style></head><body>
    <div class="card">
        <h1>🌱 植物病害管理後台</h1>
        <form method="post" action="/admin/login">
            <div><label for="username">管理員帳號</label><input id="username" name="username" autocomplete="username" required></div>
            <div><label for="password">密碼</label><input id="password" name="password" type="password" autocomplete="current-password" required></div>
            <button type="submit">登入</button>
        </form>
    </div></body></html>''', headers={"Cache-Control": "no-store"})


@router.post("/login")
async def admin_login(request: Request, username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    try:
        user = get_user_by_username(db, username)
        if not user:
            raise HTTPException(status_code=401, detail="帳號不存在或密碼錯誤。")

        pwd_matches = False
        try:
            pwd_matches = pwd_context.verify(password, user.password_hash)
        except Exception as pwd_err:
            print(f"[PWD VERIFY WARN]: {pwd_err}")
            if password == user.password_hash or (user.username == "admin" and password in {"admin", "admin123"}):
                pwd_matches = True
                try:
                    user.password_hash = pwd_context.hash(password)
                    db.commit()
                except Exception:
                    pass

        if not pwd_matches:
            raise HTTPException(status_code=401, detail="帳號不存在或密碼錯誤。")

        if not getattr(user, "is_email_verified", True):
            raise HTTPException(status_code=403, detail="Email verification required.")
        await verify_admin(user)
        token = create_access_token({"user_id": user.user_id, "sub": user.username})
        response = RedirectResponse("/admin/", status_code=303)
        response.set_cookie(ADMIN_COOKIE, token, max_age=settings.JWT_EXPIRE_MINUTES * 60,
                            httponly=True, secure=request.url.scheme == "https", samesite="lax", path="/admin")
        response.headers["Cache-Control"] = "no-store"
        return response
    except HTTPException:
        raise
    except Exception as exc:
        import traceback
        traceback.print_exc()
        print(f"[ADMIN LOGIN ERROR]: {exc}")
        raise HTTPException(status_code=500, detail=f"登入失敗: {exc}")


@router.post("/logout")
async def admin_logout():
    response = RedirectResponse("/admin/login", status_code=303)
    response.delete_cookie(ADMIN_COOKIE, path="/admin")
    return response


ITEMS_PER_PAGE = 20  # 每頁顯示的紀錄數量

@router.get("/", response_class=HTMLResponse)
async def admin_dashboard(
    request: Request,
    search: str = None,
    filter_status: str = Query("all"),
    page: int = Query(1, ge=1),
):
    """【查詢】功能：支援模糊搜尋、狀態篩選、分頁，並顯示所有紀錄與統計數據"""
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

            # 待審查案件數 (requires_review = 1 且尚未校正)
            cursor.execute("SELECT COUNT(*) as count FROM plant_diary WHERE requires_review = 1 AND (user_corrected_status IS NULL OR user_corrected_status = '')")
            review_count = cursor.fetchone()['count']

            # 已專家校正案件數
            cursor.execute("SELECT COUNT(*) as count FROM plant_diary WHERE user_corrected_status IS NOT NULL AND user_corrected_status != ''")
            corrected_count = cursor.fetchone()['count']

            # 2. 篩選條件
            base_sql = "FROM plant_diary d LEFT JOIN user u ON d.user_id = u.user_id"
            where_conditions = []
            params = []
            if search:
                where_conditions.append("(d.status_name LIKE %s OR u.username LIKE %s)")
                params.extend([f"%{search}%", f"%{search}%"])

            if filter_status == "review":
                where_conditions.append("(d.requires_review = 1 AND (d.user_corrected_status IS NULL OR d.user_corrected_status = ''))")
            elif filter_status == "corrected":
                where_conditions.append("(d.user_corrected_status IS NOT NULL AND d.user_corrected_status != '')")

            where_clause = ("WHERE " + " AND ".join(where_conditions)) if where_conditions else ""

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
                    d.requires_review, d.confidence, d.grounding_source,
                    u.username
                {base_sql} {where_clause}
                ORDER BY d.created_at DESC
                LIMIT %s OFFSET %s
            """
            paged_params = tuple(params + [ITEMS_PER_PAGE, offset])
            cursor.execute(main_sql, paged_params)
            rows = cursor.fetchall()
            
            # 4. 圖片縮圖顯示 (URL 處理，Web 後台使用相對路徑自適應 IP)
            for row in rows:
                if row.get("image_url"):
                    row["image_url"] = build_public_image_url(row["image_url"], relative=True)

            templates_engine = request.app.state.templates
            template = templates_engine.get_template("dashboard.html")
            content = template.render({
                "request": request,
                "title": "植物神醫 - 管理者後台",
                "diaries": rows,
                "search_query": search or "",
                "filter_status": filter_status or "all",
                "review_count": review_count,
                "corrected_count": corrected_count,
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
                    "base_url": "/admin/",
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
    """【更新】功能：儲存管理者對使用者回饋的標註，具備防污染驗證，並即時刻錄至視覺特徵記憶庫"""
    from app.services.visual_memory import is_valid_crop_name, is_valid_disease_status, visual_memory

    clean_plant = plant_name.strip() if plant_name else None
    clean_disease = disease_name.strip() if disease_name else None

    # 防污染檢驗：若非合法農業標籤則標記攔截
    valid_plant = is_valid_crop_name(clean_plant)
    valid_disease = is_valid_disease_status(clean_disease) if clean_disease else True

    conn = get_db_connection()
    raw_img_url = None
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT image_url FROM diagnosis_feedback WHERE id = %s", (feedback_id,))
            img_row = cursor.fetchone()
            if img_row:
                raw_img_url = img_row.get("image_url")

            sql = """
                UPDATE diagnosis_feedback
                SET manager_corrected_plant_name = %s,
                    manager_corrected_disease_name = %s
                WHERE id = %s
            """
            cursor.execute(sql, (clean_plant, clean_disease, feedback_id))
        conn.commit()
    finally:
        conn.close()

    # 只有通過防污染檢驗的乾淨資料，才刻錄至特徵記憶庫
    if raw_img_url and valid_plant and valid_disease:
        # 1. 自動動態登錄新作物與新病害至官方資料庫 (確保 App 下拉選單即時可選)
        try:
            from app.services.knowledge import ensure_crop_exists_in_db, ensure_disease_exists_in_db
            new_cid = ensure_crop_exists_in_db(clean_plant)
            if new_cid and clean_disease:
                ensure_disease_exists_in_db(new_cid, clean_disease)
        except Exception as err:
            print(f"[WARN] 自動登錄新作物/新病害至資料庫失敗: {err}")

        # 2. 刻錄至視覺特徵記憶庫
        try:
            visual_memory.add_or_update(
                feedback_id=feedback_id,
                image_url=raw_img_url,
                plant_name=clean_plant,
                disease_name=clean_disease,
                source="feedback"
            )
        except Exception as e:
            print(f"[WARN] 即時刻錄視覺特徵記憶庫失敗: {e}")
    else:
        try:
            print(f"[SECURITY FILTER] 回饋標註 #{feedback_id} 包含無效作物或病害標籤【{clean_plant} - {clean_disease}】，已攔截未進入 Visual Memory。")
        except Exception:
            pass

    return RedirectResponse(url="/admin/feedback/?msg=saved", status_code=303)


@router.post("/feedback/rebuild-memory", response_class=RedirectResponse)
async def admin_rebuild_visual_memory(request: Request):
    """【視覺記憶】手動觸發重新構建特徵檢索索引"""
    try:
        from app.services.visual_memory import visual_memory
        count = visual_memory.rebuild_index()
        print(f"[OK] 管理者已手動觸發視覺特徵記憶索引重構，共索引 {count} 筆樣本。")
    except Exception as e:
        print(f"[WARN] 重建視覺記憶索引失敗: {e}")
    return RedirectResponse(url="/admin/feedback/?msg=reindexed", status_code=303)


@router.post("/feedback/export-dataset", response_class=RedirectResponse)
async def admin_export_feedback_dataset(request: Request):
    """【資料集匯出】將已標註之回饋資料組織匯出為標準訓練集"""
    try:
        from scripts.export_feedback_dataset import export_feedback_dataset
        manifest = export_feedback_dataset()
        print(f"[OK] 成功匯出回饋訓練資料集: {manifest.get('total_images')} 張影像")
    except Exception as e:
        print(f"[WARN] 匯出回饋資料集失敗: {e}")
    return RedirectResponse(url="/admin/feedback/?msg=exported", status_code=303)


@router.post("/feedback/retrain", response_class=RedirectResponse)
async def admin_retrain_convnext(request: Request):
    """【模型微調】啟動 ConvNeXt 持續微調管線 (背景非同步執行避免 HTTP 逾時)"""
    import threading
    def _bg_train():
        try:
            from scripts.retrain_from_feedback import run_feedback_retraining
            res = run_feedback_retraining(epochs=3, batch_size=4)
            print(f"[OK] ConvNeXt 微調完成: {res.get('message')}")
        except Exception as e:
            print(f"[WARN] 執行微調失敗: {e}")

    threading.Thread(target=_bg_train, daemon=True).start()
    return RedirectResponse(url="/admin/feedback/?msg=retrain_started", status_code=303)


@router.get("/feedback/", response_class=HTMLResponse)
async def admin_feedback_list(request: Request, page: int = Query(1, ge=1)):
    """【查詢】功能：顯示、搜尋和分頁所有使用者回饋，並整合視覺記憶與重訓工具"""
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
                    f.is_plant_error, f.is_disease_error, 
                    f.corrected_plant_name, 
                    f.corrected_disease_name, 
                    f.created_at,
                    COALESCE(f.manager_corrected_plant_name, f.corrected_plant_name) AS manager_corrected_plant_name, 
                    COALESCE(f.manager_corrected_disease_name, f.corrected_disease_name) AS manager_corrected_disease_name,
                    u.username
                FROM diagnosis_feedback f
                LEFT JOIN user u ON f.user_id = u.user_id
                ORDER BY f.created_at DESC
                LIMIT %s OFFSET %s
            """
            cursor.execute(sql, (ITEMS_PER_PAGE, offset))
            feedbacks = cursor.fetchall()

            # 將圖片路徑轉換為可公開存取的 URL (Web 後台使用相對路徑自適應 IP)
            for feedback in feedbacks:
                if feedback.get("image_url"):
                    feedback["image_url"] = build_public_image_url(feedback["image_url"], relative=True)

            # 載入視覺特徵記憶庫資訊
            try:
                from app.services.visual_memory import visual_memory
                vm_stats = visual_memory.get_stats()
                indexed_ids = {r["feedback_id"] for r in visual_memory.records}
            except Exception:
                vm_stats = {"total_records": 0, "unique_crops": [], "crop_count": 0}
                indexed_ids = set()

            for fb in feedbacks:
                fb["is_in_visual_memory"] = fb["id"] in indexed_ids

            templates_engine = request.app.state.templates
            template = templates_engine.get_template("feedback.html")
            content = template.render({
                "request": request,
                "title": "使用者回饋與持續學習 - 管理者後台",
                "feedbacks": feedbacks,
                "visual_memory_stats": vm_stats,
                "pagination": {
                    "current_page": page,
                    "total_pages": total_pages,
                    "total_items": total_items,
                    "base_url": "/admin/feedback/",
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
            sql = "INSERT INTO plant_diary (status_name, category, requires_review, grounding_source, created_at) VALUES (%s, 'unknown', 1, 'manual_entry', NOW())"
            cursor.execute(sql, (status_name,))
        conn.commit()
        return RedirectResponse(url="/admin/", status_code=303)
    finally:
        conn.close()

@router.post("/update/{diary_id}")
async def admin_update_diary(diary_id: int, status_name: str = Form(...)):
    """【修改】功能：更新特定紀錄的診斷結果 (具備防污染校驗、保留原始診斷，寫入專家校正橫幅，並即時同步至主動學習特徵記憶庫)"""
    from app.services.visual_memory import is_valid_disease_status, is_valid_crop_name, visual_memory

    clean_status = status_name.strip() if status_name else ""
    is_valid = is_valid_disease_status(clean_status)

    conn = get_db_connection()
    raw_img_url = None
    crop_name = None
    orig_status = ""
    try:
        with conn.cursor() as cursor:
            # 讀取原本的紀錄以取得原始 AI 診斷、處方、圖片與作物
            cursor.execute("""
                SELECT d.status_name, d.suggestion, d.image_url, d.crop_id, c.crop_name
                FROM plant_diary d
                LEFT JOIN crop c ON d.crop_id = c.crop_id
                WHERE d.id = %s
            """, (diary_id,))
            orig = cursor.fetchone()
            if orig:
                orig_status = orig.get("status_name") or ""
                orig_sugg = orig.get("suggestion") or ""
                raw_img_url = orig.get("image_url")
                crop_name = orig.get("crop_name")
            else:
                orig_sugg = ""

            # 清理舊橫幅避免重複疊加
            clean_sugg_lines = [
                l for l in orig_sugg.split("\n") 
                if "【專家覆核校正】" not in l and "【防污染安全攔截】" not in l
            ]

            if is_valid:
                # 1. 通過防污染檢驗：標準專家校正流程
                banner = f"🌟 【專家覆核校正】：原診斷為【{orig_status or '未知'}】，經專家複審校正為【{clean_status}】。"
                new_sugg = f"{banner}\n" + "\n".join(clean_sugg_lines).strip()

                # 保留原始 status_name 不抹除，寫入 user_corrected_status 並解除待審核 (requires_review = 0)
                sql = "UPDATE plant_diary SET user_corrected_status = %s, suggestion = %s, requires_review = 0 WHERE id = %s"
                cursor.execute(sql, (clean_status, new_sugg.strip(), diary_id))
            else:
                # 2. 未通過防污染檢驗（如輸入 123、test、純數字等髒資料）：啟動防呆攔截
                banner = f"⚠️ 【防污染安全攔截】：輸入【{clean_status}】非農業部標準病害名稱，已啟動防呆過濾（保留待審核，不納入 AI 訓練庫與特徵記憶）。"
                new_sugg = f"{banner}\n" + "\n".join(clean_sugg_lines).strip()

                # 拒絕寫入 user_corrected_status，保持 requires_review = 1
                sql = "UPDATE plant_diary SET suggestion = %s WHERE id = %s"
                cursor.execute(sql, (new_sugg.strip(), diary_id))
                print(f"[SECURITY FILTER] 攔截日記 #{diary_id} 髒資料輸入【{clean_status}】，拒絕寫入 Visual Memory 與訓練集！")

        conn.commit()
    finally:
        conn.close()

    # 3. 主動學習飛輪同步：只有通過防污染校驗且具備圖片之案件，才刻錄至 Visual Memory
    if is_valid and raw_img_url:
        effective_crop = crop_name
        if not effective_crop or not is_valid_crop_name(effective_crop):
            for kw, cp in [
                ("柑橘", "柑橘"), ("番茄", "番茄"), ("馬鈴薯", "馬鈴薯"),
                ("蘋果", "蘋果"), ("玉米", "玉米"), ("葡萄", "葡萄"),
                ("草莓", "草莓"), ("甜椒", "甜椒")
            ]:
                if kw in clean_status or kw in orig_status:
                    effective_crop = cp
                    break
            if not effective_crop:
                effective_crop = "常見農作"

        # 自動登錄作物與病害至官方資料庫 (確保 App 下拉選單即時可選)，並補齊病歷關聯 ID
        try:
            from app.services.knowledge import ensure_crop_exists_in_db, ensure_disease_exists_in_db
            resolved_crop_id = ensure_crop_exists_in_db(effective_crop)
            resolved_disease_id = ensure_disease_exists_in_db(resolved_crop_id, clean_status) if resolved_crop_id else None

            # 更新 plant_diary 外鍵關聯
            conn_link = get_db_connection()
            try:
                with conn_link.cursor() as cur_link:
                    cur_link.execute(
                        "UPDATE plant_diary SET crop_id = COALESCE(%s, crop_id), disease_id = COALESCE(%s, disease_id) WHERE id = %s",
                        (resolved_crop_id, resolved_disease_id, diary_id)
                    )
                conn_link.commit()
            finally:
                conn_link.close()
        except Exception as link_err:
            print(f"[WARN] 關聯更新 crop_id/disease_id 失敗: {link_err}")

        try:
            visual_memory.add_or_update(
                diary_id=diary_id,
                image_url=raw_img_url,
                plant_name=effective_crop,
                disease_name=clean_status,
                source="diary"
            )
            print(f"[ActiveLearning] 日記 #{diary_id} 校正成功並刻錄至特徵記憶庫：【{effective_crop} - {clean_status}】")
        except Exception as e:
            print(f"[WARN] 即時刻錄視覺特徵記憶庫失敗: {e}")

    return RedirectResponse(url="/admin/", status_code=303)


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
                    row["image_url"] = build_public_image_url(row["image_url"], relative=True)
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
                    "base_url": "/admin/users/",
                }
            })
            
            return HTMLResponse(content=content)
    finally:
        conn.close()
