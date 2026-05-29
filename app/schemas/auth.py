from pydantic import BaseModel, EmailStr, Field


class UserRegister(BaseModel):
    """註冊請求。"""

    username: str
    password: str = Field(min_length=8)
    email: EmailStr
    full_name: str = ""


class UserLogin(BaseModel):
    """登入請求。"""

    username: str
    password: str


class EmailVerificationRequest(BaseModel):
    """補寄驗證信請求。"""

    email: EmailStr


class ForgotPasswordRequest(BaseModel):
    """忘記密碼請求。"""

    email: EmailStr


class ResetPasswordRequest(BaseModel):
    """使用一次性 token 重設密碼。"""

    token: str = Field(min_length=20)
    new_password: str = Field(min_length=8)
    confirm_password: str = Field(min_length=8)


class TokenData(BaseModel):
    """JWT token payload 的資料結構。"""

    username: str | None = None