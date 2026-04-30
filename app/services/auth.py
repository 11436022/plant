import datetime

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer

from app.core.config import JWT_ALGORITHM, JWT_EXPIRE_MINUTES, JWT_SECRET_KEY
from app.db.session import get_db_connection

security = HTTPBearer()


def create_access_token(payload: dict) -> str:
    """建立登入後使用的 JWT。"""

    token_payload = payload.copy()
    token_payload["exp"] = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(
        minutes=JWT_EXPIRE_MINUTES
    )
    return jwt.encode(token_payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


async def get_current_user(authorization=Depends(security)):
    """解析 Bearer Token，並回查目前登入使用者。"""

    token = authorization.credentials
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("user_id")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token.")

        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT user_id, username, role, is_email_verified
                    FROM user
                    WHERE user_id = %s
                    """,
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
    """限制只有管理員可以使用的 API。"""

    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required.")
    return current_user
