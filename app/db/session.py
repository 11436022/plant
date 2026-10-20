import os

import pymysql
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
from app.db.base import Base

load_dotenv()

user = os.getenv("DB_USER") or os.getenv("MYSQL_USERNAME") or os.getenv("MYSQL_USER") or "root"
password = os.getenv("DB_PASSWORD") or os.getenv("MYSQL_ROOT_PASSWORD") or os.getenv("MYSQL_PASSWORD")
host = os.getenv("DB_HOST") or os.getenv("MYSQL_HOST")
port = int(os.getenv("DB_PORT") or os.getenv("MYSQL_PORT") or "3306")
db_name = os.getenv("DB_NAME") or os.getenv("MYSQL_DATABASE") or "plant_db"

if not all([user, host, db_name]):
    raise ValueError("無法從 .env 讀取資料庫設定，請檢查檔案是否存在且格式正確。")

DATABASE_URL = URL.create(
    "mysql+pymysql", username=user, password=password, host=host,
    port=port, database=db_name,
)

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
        user=user,
        password=password,
        host=host,
        port=port,
        database=db_name,
        cursorclass=pymysql.cursors.DictCursor,
    )
