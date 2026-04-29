from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.core.config import API_HOST, API_PORT, API_TITLE
from app.routers import admin, auth, diaries, health, prediction
from app.services.account_recovery import ensure_auth_schema

# 取得專案根目錄，供 template 與 static 掛載使用。
BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_PATH = BASE_DIR / "static"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def create_app() -> FastAPI:
    """建立 FastAPI 應用程式。"""

    app = FastAPI(title=API_TITLE)

    # 讓 router 可以透過 app.state 取得 Jinja2 templates。
    app.state.templates = templates

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    if not STATIC_PATH.exists():
        STATIC_PATH.mkdir(parents=True, exist_ok=True)

    app.mount("/static", StaticFiles(directory=str(STATIC_PATH)), name="static")

    @app.on_event("startup")
    async def startup_event() -> None:
        # 啟動時主動補齊驗證信與忘記密碼所需的 schema，避免舊資料庫缺欄位。
        ensure_auth_schema()

    app.include_router(health.router)
    app.include_router(prediction.router)
    app.include_router(auth.router)
    app.include_router(diaries.router)
    app.include_router(admin.router)

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=API_HOST, port=API_PORT)
