import datetime
import os

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer

from app.db.session import get_db_connection

security = HTTPBearer()
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "change-me-in-env")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "1440"))


def create_access_token(payload: dict) -> str:
    """建立含有效期限的 JWT。"""

    token_payload = payload.copy()
    token_payload["exp"] = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )
    return jwt.encode(token_payload, SECRET_KEY, algorithm=ALGORITHM)


async def get_current_user(authorization=Depends(security)):
    """解析 Bearer Token 並回傳登入者。"""

    token = authorization.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("user_id")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token.")

        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT user_id, username, role FROM user WHERE user_id = %s",
                    (user_id,),
                )
                user = cursor.fetchone()
                if not user:
                    raise HTTPException(status_code=401, detail="User not found.")
                return user
        finally:
            conn.close()
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired.")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=401, detail=f"Authentication failed: {exc}")


async def verify_admin(current_user: dict = Depends(get_current_user)):
    """限制只有管理員可存取。"""

    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required.")
    return current_user
