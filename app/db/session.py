import os
from urllib.parse import urlparse, unquote
import pymysql
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
from app.db.base import Base

load_dotenv()

# 1. 優先檢查完整連線字串 (Railway / 云端提供之 DATABASE_URL / MYSQL_URL / MYSQL_PRIVATE_URL)
user = "root"
password = None
host = None
port = 3306
db_name = "plant_db"

db_url_env = os.getenv("DATABASE_URL") or os.getenv("MYSQL_URL") or os.getenv("MYSQL_PRIVATE_URL")
if db_url_env:
    try:
        parsed = urlparse(db_url_env)
        if parsed.username:
            user = unquote(parsed.username)
        if parsed.password:
            password = unquote(parsed.password)
        if parsed.hostname:
            host = parsed.hostname
        if parsed.port:
            port = parsed.port
        if parsed.path and parsed.path.lstrip("/"):
            db_name = parsed.path.lstrip("/")
    except Exception as parse_err:
        print(f"[WARN] 解析資料庫連線字串失敗: {parse_err}")

# 2. 獨立環境變數支援 (全面兼容 Railway 原生變數如 MYSQLHOST, MYSQLPORT 等)
user = os.getenv("DB_USER") or os.getenv("MYSQLUSER") or os.getenv("MYSQL_USER") or os.getenv("MYSQL_USERNAME") or user
password = os.getenv("DB_PASSWORD") or os.getenv("MYSQLPASSWORD") or os.getenv("MYSQL_PASSWORD") or os.getenv("MYSQL_ROOT_PASSWORD") or password
host = os.getenv("DB_HOST") or os.getenv("MYSQLHOST") or os.getenv("MYSQL_HOST") or host
port_val = os.getenv("DB_PORT") or os.getenv("MYSQLPORT") or os.getenv("MYSQL_PORT") or port
port = int(port_val) if port_val else 3306
db_name = os.getenv("DB_NAME") or os.getenv("MYSQLDATABASE") or os.getenv("MYSQL_DATABASE") or db_name

if not host:
    host = "127.0.0.1"
    print("[WARN] 尚未設定 DB_HOST / MYSQLHOST 環境變數，暫以 127.0.0.1 佔位。")

DATABASE_URL = URL.create(
    "mysql+pymysql", username=user, password=password, host=host,
    port=port, database=db_name,
)

# SQLAlchemy 連線與 Session 工廠 (啟用 pool_pre_ping 與 pool_recycle 防止雲端閒置斷線)
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=280,
    pool_size=10,
    max_overflow=20,
)
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
        connect_timeout=10,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
    )
