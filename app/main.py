import sys
from pathlib import Path

if sys.platform == "win32":
    try:
        if sys.stdout and hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        if sys.stderr and hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.core.config import settings
from app.routers import admin, auth, diaries, feedback, health, knowledge, prediction, webcam, weather
from app.services.account_recovery import ensure_auth_schema
from app.services import rag

# 取得專案根目錄，供 template 與 static 掛載使用。
BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_PATH = settings.STATIC_DIR
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
templates.env.auto_reload = True


def create_app() -> FastAPI:
    """建立 FastAPI 應用程式。"""
    app = FastAPI(title=settings.API_TITLE)

    # 讓 router 可以透過 app.state 取得 Jinja2 templates。
    app.state.templates = templates

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 掛載上傳檔案的目錄
    # 確保所有上傳與靜態子目錄存在（防止 Railway 全新掛載空 Volume 時拋出 RuntimeError 導致崩潰）
    settings.STATIC_DIR.mkdir(parents=True, exist_ok=True)
    settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    settings.FEEDBACK_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    settings.TEMP_DIR.mkdir(parents=True, exist_ok=True)

    # 🌟 自動將預載種子圖片與快取同步至全新掛載的 Volume (避免空 Volume 遮蔽歷史種子圖片與向量記憶庫)
    seed_static_dir = BASE_DIR / "static_seed"
    if seed_static_dir.exists():
        import shutil, os
        for root, _, files in os.walk(seed_static_dir):
            rel_path = Path(root).relative_to(seed_static_dir)
            target_subdir = settings.STATIC_DIR / rel_path
            target_subdir.mkdir(parents=True, exist_ok=True)
            for f in files:
                dest_file = target_subdir / f
                if not dest_file.exists():
                    try:
                        shutil.copy2(Path(root) / f, dest_file)
                    except Exception:
                        pass

    app.mount("/uploads", StaticFiles(directory=str(settings.UPLOAD_DIR)), name="uploads")
    app.mount("/feedback_uploads", StaticFiles(directory=str(settings.FEEDBACK_UPLOAD_DIR)), name="feedback_uploads")

    @app.get("/reset-password-web", response_class=FileResponse)
    async def get_reset_password_web_page():
        """提供重設密碼的 HTML 中介頁。"""
        target = STATIC_PATH / "reset_password.html"
        if not target.exists():
            fallback = TEMPLATES_DIR / "reset_password.html"
            if fallback.exists():
                return str(fallback)
        return str(target)

    @app.get("/photo", response_class=HTMLResponse)
    async def get_photo_diagnosis_page(request: Request):
        """提供跨平台（包含 iPhone / Safari 與 Android）即時拍照快篩與病害診斷網頁。"""
        template = templates.get_template("photo.html")
        return HTMLResponse(content=template.render({"request": request}))

    @app.get("/dashboard")
    async def redirect_dashboard():
        """提供 /dashboard 快捷轉址至管理者後台 /admin/。"""
        return RedirectResponse(url="/admin/", status_code=303)

    @app.api_route("/download-apk", methods=["GET", "HEAD"], response_class=FileResponse)
    @app.api_route("/plantdoctor.apk", methods=["GET", "HEAD"], response_class=FileResponse)
    async def download_latest_apk():
        """提供最新 Android APK 安裝檔下載，方便手機瀏覽器直接點擊安裝。"""
        candidates = [
            settings.UPLOAD_DIR / "plantdoctor.apk",
            BASE_DIR / "static_seed" / "uploads" / "plantdoctor.apk",
            settings.STATIC_DIR / "plantdoctor.apk",
            BASE_DIR / "plantdoctor.apk",
            BASE_DIR / "frontend" / "plantdoctor" / "app" / "build" / "outputs" / "apk" / "debug" / "app-debug.apk",
        ]
        for p in candidates:
            if p.exists() and p.is_file():
                return FileResponse(
                    str(p),
                    media_type="application/vnd.android.package-archive",
                    filename="plantdoctor.apk",
                )
        raise HTTPException(status_code=404, detail="APK 檔案尚未就緒")

    @app.on_event("startup")
    async def startup_event() -> None:
        # 啟動時主動補齊驗證信與忘記密碼所需的 schema，避免舊資料庫缺欄位。
        try:
            from app.db.base import Base
            from app.db.session import engine
            import app.db.models
            Base.metadata.create_all(bind=engine)
            print("[DB] 所有資料表結構驗證/建立成功！")
        except Exception as e:
            print(f"[WARN] 自動建立資料表略過: {e}")

        # 若是全新空資料庫或舊版資料庫 (診斷紀錄少於 50 筆)，自動同步最新種子資料
        try:
            from sqlalchemy import text
            from app.db.session import engine, get_db_connection
            needs_seed = False
            try:
                with engine.connect() as conn:
                    crop_cnt = conn.execute(text("SELECT count(*) FROM crop")).scalar()
                if not crop_cnt or crop_cnt == 0:
                    needs_seed = True
            except Exception:
                needs_seed = True

            if needs_seed:
                # 優先使用包含 56 筆與最新資料的 latest_seed.sql
                sql_path = Path("latest_seed.sql") if Path("latest_seed.sql").exists() else Path("init_db.sql")
                if sql_path.exists():
                    print(f"[DB] 自動執行 {sql_path.name} 同步最新資料庫紀錄...")
                    raw_sql = sql_path.read_text(encoding="utf-8")
                    db_conn = get_db_connection()
                    with db_conn.cursor() as cur:
                        for stmt in raw_sql.split(";\n"):
                            clean_s = stmt.strip()
                            if clean_s:
                                try:
                                    cur.execute(clean_s)
                                except Exception:
                                    pass
                        db_conn.commit()
                    db_conn.close()
                    print("[DB] 資料庫同步完成！")
        except Exception as seed_err:
            print(f"[WARN] 檢查/同步資料庫種子略過: {seed_err}")

        try:
            ensure_auth_schema()
        except Exception as e:
            print(f"[WARN] ensure_auth_schema 略過: {e}")
        # 載入 RAG 知識庫
        try:
            rag.load_knowledge_base()
        except Exception as e:
            print(f"[WARN] 載入 RAG 知識庫略過: {e}")
        # 預載本地 ConvNeXt 快篩模型
        try:
            from app.services.convnext import get_convnext_model
            get_convnext_model()
        except Exception as e:
            print(f"[WARN] 預載 ConvNeXt 失敗: {e}")

    # API routers (v1)
    # ----------------
    # 認證相關的 API
    app.include_router(auth.router, prefix="/api/v1/auth")

    # 其他 API
    app.include_router(prediction.router, prefix="/api/v1")
    app.include_router(diaries.router, prefix="/api/v1/diaries", tags=["Diaries"])
    app.include_router(feedback.router, prefix="/api/v1/feedback")
    app.include_router(knowledge.router, prefix="/api/v1")
    app.include_router(webcam.router, prefix="/api/v1")
    app.include_router(weather.router, prefix="/api/v1/weather")
    app.include_router(webcam.page_router)

    # Admin router (通常有自己的根路徑，不放在 /api/v1 內)
    app.include_router(admin.router)

    # Health check (通常不放在 API 版本控制內)
    app.include_router(health.router)

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host=settings.API_HOST, port=settings.API_PORT, reload=True)