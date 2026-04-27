import os

import pymysql
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
from app.db.base import Base

load_dotenv()

user = os.getenv("DB_USER")
password = os.getenv("DB_PASSWORD")
host = os.getenv("DB_HOST")
db_name = os.getenv("DB_NAME")

if not all([user, host, db_name]):
    raise ValueError("無法從 .env 讀取資料庫設定，請檢查檔案是否存在且格式正確。")

DATABASE_URL = f"mysql+pymysql://{user}:{password}@{host}/{db_name}"

# SQLAlchemy 連線與 Session 工廠。
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)


def get_db():
    """提供 FastAPI 使用的 SQLAlchemy Session。"""

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_db_connection():
    """提供直接執行 SQL 用的 PyMySQL 連線。"""

    return pymysql.connect(
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST"),
        database=os.getenv("DB_NAME"),
        cursorclass=pymysql.cursors.DictCursor,
    )
