import datetime
import hashlib
import secrets
from urllib.parse import urlencode

from fastapi import HTTPException

from app.core.config import (
    EMAIL_VERIFICATION_EXPIRE_MINUTES,
    EMAIL_VERIFY_PATH,
    FRONTEND_BASE_URL,
    PASSWORD_RESET_EXPIRE_MINUTES,
    PASSWORD_RESET_PATH,
    PUBLIC_BASE_URL,
)
from app.db.session import get_db_connection
from app.services.email import send_email

EMAIL_VERIFICATION_PURPOSE = "email_verification"
PASSWORD_RESET_PURPOSE = "password_reset"


def ensure_auth_schema() -> None:
    """補齊忘記密碼與信箱驗證所需的欄位與資料表。"""

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            if not _column_exists(cursor, "user", "is_email_verified"):
                cursor.execute(
                    """
                    ALTER TABLE user
                    ADD COLUMN is_email_verified TINYINT(1) NOT NULL DEFAULT 1
                    """
                )
            if not _column_exists(cursor, "user", "email_verified_at"):
                cursor.execute(
                    """
                    ALTER TABLE user
                    ADD COLUMN email_verified_at DATETIME NULL DEFAULT NULL
                    """
                )
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


def issue_email_verification(user_id: int, username: str, email: str) -> datetime.datetime:
    """建立信箱驗證 token 並寄出驗證信。"""

    token, expires_at = _issue_token(
        user_id=user_id,
        purpose=EMAIL_VERIFICATION_PURPOSE,
        expires_in_minutes=EMAIL_VERIFICATION_EXPIRE_MINUTES,
    )
    verify_url = _build_url(PUBLIC_BASE_URL, EMAIL_VERIFY_PATH, token)
    send_email(
        to_email=email,
        subject="Plant 帳號驗證信",
        text_body=(
            f"{username} 您好：\n\n"
            f"請點擊以下連結完成信箱驗證：\n{verify_url}\n\n"
            f"此連結將於 {expires_at.isoformat()} UTC 失效。"
        ),
        html_body=(
            f"<p>{username} 您好：</p>"
            f"<p>請點擊以下連結完成信箱驗證：</p>"
            f'<p><a href="{verify_url}">{verify_url}</a></p>'
            f"<p>此連結將於 {expires_at.isoformat()} UTC 失效。</p>"
        ),
    )
    return expires_at


def send_password_reset_email(user_id: int, username: str, email: str) -> datetime.datetime:
    """建立一次性重設密碼 token，並寄出重設連結。"""

    token, expires_at = _issue_token(
        user_id=user_id,
        purpose=PASSWORD_RESET_PURPOSE,
        expires_in_minutes=PASSWORD_RESET_EXPIRE_MINUTES,
    )
    reset_url = _build_url(FRONTEND_BASE_URL, PASSWORD_RESET_PATH, token)
    send_email(
        to_email=email,
        subject="Plant 重設密碼通知",
        text_body=(
            f"{username} 您好：\n\n"
            f"請使用以下一次性重設連結：\n{reset_url}\n\n"
            f"若前端需要直接使用 token，也可以使用下列一次性 token：\n{token}\n\n"
            f"此連結將於 {expires_at.isoformat()} UTC 失效。"
        ),
        html_body=(
            f"<p>{username} 您好：</p>"
            f"<p>請使用以下一次性重設連結：</p>"
            f'<p><a href="{reset_url}">{reset_url}</a></p>'
            f"<p>若前端需要直接使用 token，也可以使用下列一次性 token：</p>"
            f"<p><code>{token}</code></p>"
            f"<p>此連結將於 {expires_at.isoformat()} UTC 失效。</p>"
        ),
    )
    return expires_at


def verify_email_token(token: str) -> int:
    """消耗驗證 token，並將使用者標記為已驗證。"""

    record = _consume_token(token, EMAIL_VERIFICATION_PURPOSE)
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
                (record["user_id"],),
            )
        conn.commit()
    finally:
        conn.close()
    return record["user_id"]


def consume_password_reset_token(token: str) -> dict:
    """驗證並消耗重設密碼 token。"""

    return _consume_token(token, PASSWORD_RESET_PURPOSE)


def update_password(user_id: int, password_hash: str) -> None:
    """更新密碼後，將同用途 token 一併作廢，避免重複使用。"""

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "UPDATE user SET password_hash = %s WHERE user_id = %s",
                (password_hash, user_id),
            )
            cursor.execute(
                """
                UPDATE user_one_time_tokens
                SET used_at = COALESCE(used_at, UTC_TIMESTAMP())
                WHERE user_id = %s AND purpose = %s AND used_at IS NULL
                """,
                (user_id, PASSWORD_RESET_PURPOSE),
            )
        conn.commit()
    finally:
        conn.close()


def _issue_token(user_id: int, purpose: str, expires_in_minutes: int) -> tuple[str, datetime.datetime]:
    """建立一次性 token，並讓同用途舊 token 失效。"""

    ensure_auth_schema()
    raw_token = secrets.token_urlsafe(32)
    token_hash = _hash_token(raw_token)
    expires_at = datetime.datetime.utcnow() + datetime.timedelta(minutes=expires_in_minutes)

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                UPDATE user_one_time_tokens
                SET used_at = COALESCE(used_at, UTC_TIMESTAMP())
                WHERE user_id = %s AND purpose = %s AND used_at IS NULL
                """,
                (user_id, purpose),
            )
            cursor.execute(
                """
                INSERT INTO user_one_time_tokens (user_id, purpose, token_hash, expires_at)
                VALUES (%s, %s, %s, %s)
                """,
                (user_id, purpose, token_hash, expires_at),
            )
        conn.commit()
    finally:
        conn.close()

    return raw_token, expires_at


def _consume_token(token: str, purpose: str) -> dict:
    """驗證 token 是否存在、是否過期、是否已被使用，並在成功後立刻作廢。"""

    ensure_auth_schema()
    token_hash = _hash_token(token)

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, user_id, expires_at, used_at
                FROM user_one_time_tokens
                WHERE token_hash = %s AND purpose = %s
                """,
                (token_hash, purpose),
            )
            record = cursor.fetchone()
            if not record:
                raise HTTPException(status_code=400, detail="Invalid token.")
            if record["used_at"] is not None:
                raise HTTPException(status_code=400, detail="Token has already been used.")
            if record["expires_at"] <= datetime.datetime.utcnow():
                raise HTTPException(status_code=400, detail="Token has expired.")

            cursor.execute(
                """
                UPDATE user_one_time_tokens
                SET used_at = UTC_TIMESTAMP()
                WHERE id = %s AND used_at IS NULL
                """,
                (record["id"],),
            )
            if cursor.rowcount != 1:
                raise HTTPException(status_code=400, detail="Token is no longer valid.")
        conn.commit()
    finally:
        conn.close()

    return record


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
