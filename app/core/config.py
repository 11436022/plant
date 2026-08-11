from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """管理應用程式的所有設定。"""

    # .env 檔案路徑與基本設定
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # 專案根目錄與靜態資源路徑
    BASE_DIR: Path = Path(__file__).resolve().parents[2]
    STATIC_DIR: Path = BASE_DIR / "static"
    UPLOAD_DIR: Path = STATIC_DIR / "uploads" # 使用者日記圖片
    FEEDBACK_UPLOAD_DIR: Path = STATIC_DIR / "feedback_uploads" # 診斷回饋圖片

    # API 基本設定
    API_TITLE: str = "Plant API"
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    WIFI_HOST_IP: str = "127.0.0.1"

    # 對外網址設定
    @property
    def FRONTEND_BASE_URL(self) -> str:
        """基於 WIFI_HOST_IP 動態計算前端基礎 URL。"""
        return f"http://{self.WIFI_HOST_IP}:8000"

    @property
    def PUBLIC_BASE_URL(self) -> str:
        """公開可訪問的基礎 URL，通常與前端 URL 相同。"""
        return self.FRONTEND_BASE_URL

    EMAIL_VERIFY_PATH: str = "/api/v1/auth/user/verify-email"
    PASSWORD_RESET_PATH: str = "/reset-password"

    # JWT 設定
    JWT_SECRET_KEY: str = "change-me-in-env"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 1440

    # SMTP 設定，用於寄送驗證信與重設密碼信
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USERNAME: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_FROM_EMAIL: Optional[str] = None
    SMTP_FROM_NAME: str = API_TITLE

    # 中央氣象署開放資料API金鑰
    CWB_API_KEY: Optional[str] = None
    SMTP_USE_TLS: bool = True
    SMTP_USE_SSL: bool = False

    # 一次性 token 的有效時間
    EMAIL_VERIFICATION_EXPIRE_MINUTES: int = 1440
    PASSWORD_RESET_EXPIRE_MINUTES: int = 30

    def __init__(self, **values):
        super().__init__(**values)
        # 確保上傳目錄存在
        self.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        self.FEEDBACK_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

        # 如果沒有設定 FROM_EMAIL，預設使用 USERNAME
        if self.SMTP_USERNAME and not self.SMTP_FROM_EMAIL:
            self.SMTP_FROM_EMAIL = self.SMTP_USERNAME


# 建立一個全域的 settings 物件供其他模組使用
settings = Settings()