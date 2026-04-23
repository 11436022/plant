from pydantic import BaseModel, EmailStr


class UserRegister(BaseModel):
    """註冊請求。"""

    username: str
    password: str
    email: EmailStr
    full_name: str | None = None


class UserLogin(BaseModel):
    """登入請求。"""

    username: str
    password: str
