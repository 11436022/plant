import os
import socket
from fastapi import APIRouter
from app.db import session as db_session
from app.core.config import settings

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
        "smtp_host": settings.SMTP_HOST,
        "smtp_user": settings.SMTP_USERNAME,
        "has_smtp_password": bool(settings.SMTP_PASSWORD),
        "smtp_env_keys": [k for k in os.environ.keys() if "SMTP" in k],
    }


@router.get("/health/smtp")
def check_smtp():
    import smtplib
    ports_to_test = [587, 465, 25]
    port_results = {}
    for p in ports_to_test:
        try:
            sock = socket.create_connection(("smtp.gmail.com", p), timeout=2)
            sock.close()
            port_results[p] = "connected"
        except Exception as e:
            port_results[p] = f"{type(e).__name__}: {e}"
            
    res = {
        "host": settings.SMTP_HOST,
        "port": settings.SMTP_PORT,
        "user": settings.SMTP_USERNAME,
        "port_tests": port_results,
    }
    return res
