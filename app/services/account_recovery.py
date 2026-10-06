import datetime
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db import models
from app.db.session import get_db, get_db_connection
from app.services.email import send_email

EMAIL_VERIFICATION_PURPOSE = "email_verification"
PASSWORD_RESET_PURPOSE = "password_reset"


def ensure_auth_schema() -> None:
    """補齊忘記密碼與信箱驗證所需的欄位與資料表，以及 PlantDiary 缺少的欄位。"""

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # 1. User 表相關
            if not _column_exists(cursor, "user", "is_email_verified"):
                cursor.execute("ALTER TABLE user ADD COLUMN is_email_verified TINYINT(1) NOT NULL DEFAULT 1")
            if not _column_exists(cursor, "user", "email_verified_at"):
                cursor.execute("ALTER TABLE user ADD COLUMN email_verified_at DATETIME NULL DEFAULT NULL")

            # 2. PlantDiary 表相關 (解決 500 錯誤的關鍵)
            if not _column_exists(cursor, "plant_diary", "user_corrected_status"):
                cursor.execute("ALTER TABLE plant_diary ADD COLUMN user_corrected_status VARCHAR(100) NULL DEFAULT NULL")

            # 3. Token 表相關
            if not _table_exists(cursor, "user_one_time_tokens"):
                cursor.execute(
                    """
                    CREATE TABLE user_one_time_tokens (
                        id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
                        user_id INT NOT NULL,
                        purpose VARCHAR(32) NOT NULL,
                        token_hash CHAR(64) NOT NULL,
                        expires_at DATETIME NOT NULL,
                        used_at DATETIME NULL DEFAULT NULL,
                        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE KEY uq_user_one_time_tokens_token_hash (token_hash),
                        KEY ix_user_one_time_tokens_user_purpose (user_id, purpose),
                        CONSTRAINT fk_user_one_time_tokens_user
                            FOREIGN KEY (user_id) REFERENCES user(user_id)
                            ON DELETE CASCADE
                    )
                    """
                )
        conn.commit()
    finally:
        conn.close()


def issue_email_verification(
    user_id: int, username: str, email: str, db: Session = Depends(get_db)
) -> datetime:
    """建立信箱驗證 token 並寄出驗證信。"""

    token, expires_at = _issue_token(
        user_id=user_id,
        purpose=EMAIL_VERIFICATION_PURPOSE,
        expires_in_minutes=settings.EMAIL_VERIFICATION_EXPIRE_MINUTES,
        db=db,
    )
    verify_url = _build_url(settings.PUBLIC_BASE_URL, settings.EMAIL_VERIFY_PATH, token)
    expires_str = expires_at.strftime("%Y-%m-%d %H:%M:%S")
    send_email(
        to_email=email,
        subject="Plant 帳號驗證信",
        text_body=(
            f"{username} 您好：\n\n"
            f"請點擊以下連結完成信箱驗證：\n{verify_url}\n\n"
            f"此連結將於 {expires_str} UTC 失效。"
        ),
        html_body=(
            f'<div style="font-family: -apple-system, BlinkMacSystemFont, \'Segoe UI\', Roboto, sans-serif; max-width: 560px; margin: 0 auto; padding: 24px; border: 1px solid #e0e0e0; border-radius: 12px; background: #ffffff;">'
            f'<h2 style="color: #2E7D32; margin-top: 0;">🌱 植物醫生 Plant Doctor</h2>'
            f'<p style="color: #333; font-size: 15px;">{username} 您好：</p>'
            f'<p style="color: #555; font-size: 14px; line-height: 1.5;">感謝您註冊植物醫生！請點擊下方按鈕以完成信箱驗證：</p>'
            f'<div style="text-align: center; margin: 28px 0;">'
            f'<a href="{verify_url}" style="background-color: #2E7D32; color: #ffffff; padding: 12px 28px; text-decoration: none; border-radius: 8px; font-weight: bold; font-size: 15px; display: inline-block;">點此完成信箱驗證</a>'
            f'</div>'
            f'<hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">'
            f'<p style="color: #999; font-size: 12px; margin-bottom: 0;">此驗證連結將於 {expires_str} UTC 失效。若非您本人註冊，請忽略此信件。</p>'
            f'</div>'
        ),
    )
    return expires_at


def send_password_reset_email(
    user_id: int, username: str, email: str, db: Session = Depends(get_db)
) -> datetime:
    """建立一次性重設密碼 token，並寄出重設連結。"""

    token, expires_at = _issue_token(
        user_id=user_id,
        purpose=PASSWORD_RESET_PURPOSE,
        expires_in_minutes=settings.PASSWORD_RESET_EXPIRE_MINUTES,
        db=db,
    )
    # 產生指向 /app-redirect 中轉站的 URL
    params = {
        "target": "plantdoctor://reset/reset-password",
        "token": token,
    }
    reset_url = f"{settings.PUBLIC_BASE_URL}/api/v1/auth/app-redirect?{urlencode(params)}"
    expires_str = expires_at.strftime("%Y-%m-%d %H:%M:%S")
    send_email(
        to_email=email,
        subject="Plant 重設密碼通知",
        text_body=(
            f"{username} 您好：\n\n"
            f"請點擊以下連結以重設您的密碼：\n{reset_url}\n\n"
            f"若前端需要直接使用 token，也可以使用下列一次性 token：\n{token}\n\n"
            f"此連結將於 {expires_str} UTC 失效。"
        ),
        html_body=(
            f'<div style="font-family: -apple-system, BlinkMacSystemFont, \'Segoe UI\', Roboto, sans-serif; max-width: 560px; margin: 0 auto; padding: 24px; border: 1px solid #e0e0e0; border-radius: 12px; background: #ffffff;">'
            f'<h2 style="color: #2E7D32; margin-top: 0;">🌱 植物醫生 Plant Doctor</h2>'
            f'<p style="color: #333; font-size: 15px;">{username} 您好：</p>'
            f'<p style="color: #555; font-size: 14px; line-height: 1.5;">我們收到了重設您密碼的請求。請點擊下方按鈕前往重設密碼：</p>'
            f'<div style="text-align: center; margin: 28px 0;">'
            f'<a href="{reset_url}" style="background-color: #2E7D32; color: #ffffff; padding: 12px 28px; text-decoration: none; border-radius: 8px; font-weight: bold; font-size: 15px; display: inline-block;">點此重設密碼</a>'
            f'</div>'
            f'<p style="color: #666; font-size: 13px; margin-bottom: 6px;">若需在 App 內手動驗證，亦可使用下列一次性 Token：</p>'
            f'<div style="background: #f5f5f5; padding: 10px 14px; border-radius: 6px; font-family: monospace; font-size: 13px; color: #333; word-break: break-all;">{token}</div>'
            f'<hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">'
            f'<p style="color: #999; font-size: 12px; margin-bottom: 0;">此連結與 Token 將於 {expires_str} UTC 失效。若非您本人操作，請忽略此信件。</p>'
            f'</div>'
        ),
    )
    return expires_at


def verify_email_token(token: str, db: Session = Depends(get_db)) -> int:
    """消耗驗證 token，並將使用者標記為已驗證。"""

    record = _consume_token(token, EMAIL_VERIFICATION_PURPOSE, db)
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                UPDATE user
                SET is_email_verified = 1,
                    email_verified_at = UTC_TIMESTAMP()
                WHERE user_id = %s
                """,
                (record.user_id,),
            )
        conn.commit()
    finally:
        conn.close()
    return record.user_id


def consume_password_reset_token(token: str, db: Session = Depends(get_db)) -> models.UserOneTimeToken:
    """驗證並消耗重設密碼 token。"""

    return _consume_token(token, PASSWORD_RESET_PURPOSE, db)


def update_password(user_id: int, password_hash: str, db: Session) -> None:
    """使用 ORM 更新密碼後，將同用途 token 一併作廢，避免重複使用。"""
    # 1. 更新使用者密碼
    user = db.query(models.User).filter(models.User.user_id == user_id).first()
    if user:
        user.password_hash = password_hash

    # 2. 作廢所有未使用的同類型 token
    now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
    db.query(models.UserOneTimeToken).filter(
        models.UserOneTimeToken.user_id == user_id,
        models.UserOneTimeToken.purpose == PASSWORD_RESET_PURPOSE,
        models.UserOneTimeToken.used_at.is_(None),
    ).update({"used_at": now_utc})

    db.commit()


def _issue_token(
    user_id: int, purpose: str, expires_in_minutes: int, db: Session
) -> tuple[str, datetime]:
    """使用 ORM 建立一次性 token，並讓同用途舊 token 失效。"""

    raw_token = secrets.token_urlsafe(32)
    token_hash = _hash_token(raw_token)

    # 統一使用 UTC 時間
    now_utc = datetime.now(timezone.utc).replace(tzinfo=None) # 轉為 naive
    expires_at_utc = now_utc + timedelta(minutes=expires_in_minutes)

    # 1. 使用 ORM 更新，讓同用途的舊 token 失效
    db.query(models.UserOneTimeToken).filter(
        models.UserOneTimeToken.user_id == user_id,
        models.UserOneTimeToken.purpose == purpose,
        models.UserOneTimeToken.used_at.is_(None), # SQLAlchemy 方式檢查 IS NULL
    ).update({"used_at": now_utc})

    # 2. 使用 ORM 創建新 token
    new_token = models.UserOneTimeToken(
        user_id=user_id,
        purpose=purpose,
        token_hash=token_hash,
        expires_at=expires_at_utc,
        created_at=now_utc,
    )
    db.add(new_token)
    db.commit()

    return raw_token, expires_at_utc


def _consume_token(token: str, purpose: str, db: Session) -> models.UserOneTimeToken:
    """使用 ORM 驗證 token 是否存在、是否過期、是否已被使用，並在成功後立刻作廢。"""
    token_hash = _hash_token(token)

    # 1. 使用 ORM 查詢 token
    token_record = (
        db.query(models.UserOneTimeToken)
        .filter(
            models.UserOneTimeToken.token_hash == token_hash,
            models.UserOneTimeToken.purpose == purpose,
        )
        .first()
    )

    # 2. 驗證 token 狀態
    if not token_record:
        raise HTTPException(status_code=400, detail="Invalid token.")
    if token_record.used_at is not None:
        raise HTTPException(status_code=400, detail="Token has already been used.")

    # 統一使用 UTC 時間進行比較
    now_utc = datetime.now(timezone.utc).replace(tzinfo=None) # 轉為 naive
    if token_record.expires_at <= now_utc:
        raise HTTPException(status_code=400, detail="Token has expired.")

    # 3. 更新 token 狀態 (作廢)
    token_record.used_at = now_utc
    db.commit()
    db.refresh(token_record)

    return token_record



def _build_url(base_url: str, path: str, token: str) -> str:
    """組合出前端或後端可直接打開的連結。"""

    query = urlencode({"token": token})
    return f"{base_url.rstrip('/')}{path}?{query}"


def _hash_token(token: str) -> str:
    """僅保存 token 雜湊值，避免資料庫外洩時明碼可直接重放。"""

    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _table_exists(cursor, table_name: str) -> bool:
    cursor.execute(
        """
        SELECT 1
        FROM information_schema.tables
        WHERE table_schema = DATABASE() AND table_name = %s
        LIMIT 1
        """,
        (table_name,),
    )
    return cursor.fetchone() is not None


def _column_exists(cursor, table_name: str, column_name: str) -> bool:
    cursor.execute(
        """
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = DATABASE()
          AND table_name = %s
          AND column_name = %s
        LIMIT 1
        """,
        (table_name, column_name),
    )
    return cursor.fetchone() is not None