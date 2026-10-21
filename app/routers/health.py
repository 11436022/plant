import os
from fastapi import APIRouter
from app.db import session as db_session

router = APIRouter(tags=["health"])


@router.get("/")
def read_root():
    """基本健康檢查。"""
    return {"message": "Plant API is running. Open /docs for the API docs."}


@router.get("/health")
def health_check():
    """系統與資料庫連線診斷。"""
    return {
        "status": "running",
        "db_host": db_session.host,
        "db_user": db_session.user,
        "db_name": db_session.db_name,
        "db_port": db_session.port,
        "has_password": bool(db_session.password),
        "has_mysql_url": bool(os.getenv("MYSQL_URL") or os.getenv("DATABASE_URL")),
        "relevant_env_keys": [k for k in os.environ.keys() if "DB" in k or "MYSQL" in k],
    }
