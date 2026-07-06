import datetime

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import User
from app.db.session import get_db
from app.schemas.auth import TokenData
from app.crud import get_user_by_id, get_user_by_username

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def create_access_token(payload: dict) -> str:
    """建立登入後使用的 JWT。"""

    token_payload = payload.copy()
    token_payload["exp"] = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(
        minutes=settings.JWT_EXPIRE_MINUTES
    )
    return jwt.encode(token_payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def get_current_user(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)) -> User:
    """
    從 token 取得當前使用者，並從資料庫中驗證其存在。
    優先使用 user_id，若無則向下相容使用 username。
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        user_id: int | None = payload.get("user_id")
        username: str | None = payload.get("sub")  # Fallback for older tokens

        if user_id is None and username is None:
            raise credentials_exception

    except (JWTError, ValidationError):
        raise credentials_exception

    user: User | None = None
    if user_id:
        user = get_user_by_id(db, user_id=user_id)

    # 如果 token 中沒有 user_id (舊版 token)，或基於 user_id 找不到使用者，
    # 則嘗試使用 username 作為備用方案。
    if user is None and username:
        user = get_user_by_username(db, username=username)

    if user is None:
        raise credentials_exception
    return user


async def verify_admin(current_user: dict = Depends(get_current_user)):
    """限制只有管理員可以使用的 API。"""

    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required.")
    return current_user