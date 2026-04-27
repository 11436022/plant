import os
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.core.config import API_HOST, API_PORT, API_TITLE
from app.routers import admin, auth, diaries, health, prediction

# --- 核心路徑修正 ---
# 取得目前檔案 (app/main.py) 的絕對路徑，然後往上跳一級到 plant/
BASE_DIR = Path(__file__).resolve().parent.parent

# 設定 templates 和 static 的絕對路徑
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_PATH = BASE_DIR / "static"

# 初始化 Jinja2
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

def create_app() -> FastAPI:
    """建立 FastAPI 應用。"""

    app = FastAPI(title=API_TITLE)
    
    # 存入 app 狀態供 router 使用
    app.state.templates = templates

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # 檢查資料夾是否存在，避免 RuntimeError
    if not STATIC_PATH.exists():
        print(f"⚠️ 警告: 找不到靜態資料夾 {STATIC_PATH}，正在嘗試建立...")
        STATIC_PATH.mkdir(parents=True, exist_ok=True)

    # 使用絕對路徑掛載
    app.mount("/static", StaticFiles(directory=str(STATIC_PATH)), name="static")

    # 註冊路由
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