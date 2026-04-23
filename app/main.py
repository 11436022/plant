from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import API_HOST, API_PORT, API_TITLE, STATIC_DIR
from app.routers import admin, auth, diaries, health, prediction


def create_app() -> FastAPI:
    """建立 FastAPI 應用。"""

    app = FastAPI(title=API_TITLE)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

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
