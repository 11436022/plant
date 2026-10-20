import os
from urllib.parse import urlparse, unquote
import pymysql
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
from app.db.base import Base

load_dotenv()

# 1. 預設值
user = "root"
password = None
host = None
port = 3306
db_name = "plant_db"

# 2. 優先檢查完整連線字串 (Railway / 雲端提供之 DATABASE_URL / MYSQL_URL / MYSQL_PRIVATE_URL)
db_url_env = os.getenv("DATABASE_URL") or os.getenv("MYSQL_URL") or os.getenv("MYSQL_PRIVATE_URL")
if db_url_env:
    try:
        # 清洗可能多帶的變數名稱與等號 (例如 'MYSQL_URL = mysql://...')
        clean_url = db_url_env.strip()
        if "mysql://" in clean_url:
            clean_url = "mysql://" + clean_url.split("mysql://", 1)[1].strip()
        elif "mysql+pymysql://" in clean_url:
            clean_url = "mysql+pymysql://" + clean_url.split("mysql+pymysql://", 1)[1].strip()
        elif "=" in clean_url:
            clean_url = clean_url.split("=", 1)[1].strip()

        parsed = urlparse(clean_url)
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

# 3. 獨立環境變數支援 (若有 Railway 原生變數如 MYSQLHOST，或自訂非 127.0.0.1 之 DB_HOST，則更新之)
env_db_host = os.getenv("DB_HOST") or os.getenv("MYSQL_HOST")
env_mysql_host = os.getenv("MYSQLHOST")

# 如果環境變數中有 Railway 提供的遠端 host (MYSQLHOST)，優先使用
if env_mysql_host:
    host = env_mysql_host

# 如果 DB_HOST 不是 127.0.0.1 或 localhost，才使用自訂 DB_HOST (避免被範本中的 127.0.0.1 覆蓋)
if env_db_host and env_db_host not in {"127.0.0.1", "localhost", "0.0.0.0"}:
    host = env_db_host

# 如果 host 依然是空，且環境變數只有 127.0.0.1
if not host:
    host = env_db_host or "127.0.0.1"

# 帳號、密碼、連接埠、資料庫名
env_user = os.getenv("MYSQLUSER") or os.getenv("DB_USER") or os.getenv("MYSQL_USER")
if env_user:
    user = env_user

env_pwd = os.getenv("MYSQLPASSWORD") or os.getenv("DB_PASSWORD") or os.getenv("MYSQL_PASSWORD")
if env_pwd:
    password = env_pwd

env_port = os.getenv("MYSQLPORT") or os.getenv("DB_PORT") or os.getenv("MYSQL_PORT")
if env_port:
    try:
        port = int(env_port)
    except ValueError:
        pass

env_dbname = os.getenv("MYSQLDATABASE") or os.getenv("DB_NAME") or os.getenv("MYSQL_DATABASE")
if env_dbname:
    db_name = env_dbname

if host in {"127.0.0.1", "localhost"}:
    print(f"[WARN] 目前資料庫主機為 {host}，若處於雲端容器環境將無法連接本機 MySQL。請設定 MYSQL_URL 或提供雲端 DB_HOST。")

DATABASE_URL = URL.create(
    "mysql+pymysql", username=user, password=password, host=host,
    port=port, database=db_name,
)

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
