from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.core.config import settings
from app.routers import admin, auth, diaries, health, prediction, knowledge, feedback
from app.services.account_recovery import ensure_auth_schema

# 取得專案根目錄，供 template 與 static 掛載使用。
BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_PATH = settings.STATIC_DIR
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


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
    app.mount("/uploads", StaticFiles(directory=str(settings.UPLOAD_DIR)), name="uploads")
    app.mount("/feedback_uploads", StaticFiles(directory=str(settings.FEEDBACK_UPLOAD_DIR)), name="feedback_uploads")

    @app.get("/reset-password-web", response_class=FileResponse)
    async def get_reset_password_web_page():
        """提供重設密碼的 HTML 中介頁。"""
        return str(STATIC_PATH / "reset_password.html")

    @app.on_event("startup")
    async def startup_event() -> None:
        # 啟動時主動補齊驗證信與忘記密碼所需的 schema，避免舊資料庫缺欄位。
        ensure_auth_schema()

    # API routers (v1)
    # ----------------
    # 認證相關的 API
    app.include_router(auth.router, prefix="/api/v1/auth")

    # 其他 API
    app.include_router(prediction.router, prefix="/api/v1")
    app.include_router(diaries.router, prefix="/api/v1/diaries", tags=["Diaries"])
    app.include_router(knowledge.router, prefix="/api/v1")
    app.include_router(feedback.router, prefix="/api/v1/feedback", tags=["Feedback"])

    # Admin router (通常有自己的根路徑，不放在 /api/v1 內)
    app.include_router(admin.router)

    # Health check (通常不放在 API 版本控制內)
    app.include_router(health.router)

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=settings.API_HOST, port=settings.API_PORT)