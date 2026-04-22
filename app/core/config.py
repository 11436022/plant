from pathlib import Path

from dotenv import load_dotenv

# 先載入專案根目錄的 .env。
load_dotenv()

BASE_DIR = Path(__file__).resolve().parents[2]
STATIC_DIR = BASE_DIR / "static"
UPLOAD_DIR = STATIC_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

API_TITLE = "Plant API"
API_HOST = "0.0.0.0"
API_PORT = 8000
PUBLIC_BASE_URL = "http://127.0.0.1:8000"
