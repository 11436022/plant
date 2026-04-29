import os
from pathlib import Path

from dotenv import load_dotenv

# 載入環境變數，讓本機開發與部署都能用同一組設定來源。
load_dotenv()


def _env_bool(name: str, default: bool = False) -> bool:
    """將環境變數安全轉成布林值。"""

    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


# 專案根目錄與靜態資源路徑。
BASE_DIR = Path(__file__).resolve().parents[2]
STATIC_DIR = BASE_DIR / "static"
UPLOAD_DIR = STATIC_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# API 基本設定。
API_TITLE = os.getenv("API_TITLE", "Plant API")
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))

# 對外網址設定。
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", f"http://127.0.0.1:{API_PORT}")
FRONTEND_BASE_URL = os.getenv("FRONTEND_BASE_URL", PUBLIC_BASE_URL)
EMAIL_VERIFY_PATH = os.getenv("EMAIL_VERIFY_PATH", "/user/verify-email")
PASSWORD_RESET_PATH = os.getenv("PASSWORD_RESET_PATH", "/reset-password")

# JWT 設定。
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "change-me-in-env")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "1440"))

# SMTP 設定，用於寄送驗證信與重設密碼信。
SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SMTP_FROM_EMAIL = os.getenv("SMTP_FROM_EMAIL") or SMTP_USERNAME
SMTP_FROM_NAME = os.getenv("SMTP_FROM_NAME", API_TITLE)
SMTP_USE_TLS = _env_bool("SMTP_USE_TLS", True)
SMTP_USE_SSL = _env_bool("SMTP_USE_SSL", False)

# 一次性 token 的有效時間。
EMAIL_VERIFICATION_EXPIRE_MINUTES = int(os.getenv("EMAIL_VERIFICATION_EXPIRE_MINUTES", "1440"))
PASSWORD_RESET_EXPIRE_MINUTES = int(os.getenv("PASSWORD_RESET_EXPIRE_MINUTES", "30"))
