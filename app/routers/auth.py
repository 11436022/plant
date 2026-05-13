from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import OAuth2PasswordRequestForm
from passlib.context import CryptContext

from app.db.session import get_db_connection
from app.db.models import User
from app.schemas.auth import (
    EmailVerificationRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    UserLogin,
    UserRegister,
)
from app.services.account_recovery import (
    consume_password_reset_token,
    ensure_auth_schema,
    issue_email_verification,
    send_password_reset_email,
    update_password,
    verify_email_token,
)
from app.services.auth import create_access_token, get_current_user

router = APIRouter(tags=["auth"])
pwd_context = CryptContext(schemes=["bcrypt"], bcrypt__ident="2b")


@router.post("/users/register")
async def register_user(user: UserRegister):
    """建立帳號，並寄出信箱驗證信。"""

    ensure_auth_schema()
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT user_id FROM user WHERE username = %s OR email = %s",
                (user.username, user.email),
            )
            if cursor.fetchone():
                raise HTTPException(status_code=400, detail="Username or email already exists.")

            hashed_password = pwd_context.hash(user.password)
            cursor.execute(
                """
                INSERT INTO user (username, password_hash, email, full_name, is_email_verified)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (user.username, hashed_password, user.email, user.full_name, 0),
            )
            user_id = cursor.lastrowid
        conn.commit()
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Registration failed: {exc}")
    finally:
        conn.close()

    # 註冊成功後仍保留帳號，即使寄信失敗也可透過補寄流程重送。
    email_sent = True
    warning = None
    try:
        issue_email_verification(user_id, user.username, user.email)
    except Exception as exc:
        email_sent = False
        warning = str(exc)

    return {
        "status": "success",
        "message": f"User {user.username} registered.",
        "verification_required": True,
        "email_sent": email_sent,
        "warning": warning,
    }


@router.post("/login")
async def login_user(form_data: OAuth2PasswordRequestForm = Depends()):
    """登入帳號，未驗證信箱者不可取得 JWT。"""

    ensure_auth_schema()
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT user_id, username, email, password_hash, role, is_email_verified
                FROM user
                WHERE username = %s
                """,
                (form_data.username,),
            )
            db_user = cursor.fetchone()
            if not db_user:
                raise HTTPException(status_code=400, detail="Invalid username or password.")
            if not pwd_context.verify(form_data.password, db_user["password_hash"]):
                raise HTTPException(status_code=400, detail="Invalid username or password.")
            if not db_user.get("is_email_verified"):
                raise HTTPException(
                    status_code=403,
                    detail="Email not verified. Please verify your email before logging in.",
                )

            token = create_access_token(
                {
                    "sub": db_user["username"],
                    "user_id": db_user["user_id"],
                    "role": db_user["role"],
                }
            )
            return {
                "status": "success",
                "message": "Login successful.",
                "access_token": token,
                "token_type": "bearer",
            }
    finally:
        conn.close()


@router.get("/user/me")
async def get_user_profile(current_user: User = Depends(get_current_user)):
    """取得目前登入者的基本資料。"""

    # get_current_user 已經從資料庫中獲取了完整的 User 物件，
    # 我們可以直接使用它，無需再次查詢資料庫。
    return {
        "status": "success",
        "data": {
            "username": current_user.username,
            "email": current_user.email,
            "full_name": current_user.full_name,
            "created_at": current_user.created_at,
            "is_email_verified": current_user.is_email_verified,
            "email_verified_at": current_user.email_verified_at,
        },
    }


@router.post("/user/verify-email/request")
async def request_email_verification(payload: EmailVerificationRequest):
    """補寄驗證信；回應固定化，避免直接暴露帳號是否存在。"""

    ensure_auth_schema()
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT user_id, username, email, is_email_verified
                FROM user
                WHERE email = %s
                """,
                (payload.email,),
            )
            db_user = cursor.fetchone()
    finally:
        conn.close()

    if db_user and not db_user.get("is_email_verified"):
        try:
            issue_email_verification(db_user["user_id"], db_user["username"], db_user["email"])
        except Exception:
            # 補寄端點維持通用成功回應，避免成為探測信箱存在性的工具。
            pass

    return {
        "status": "success",
        "message": "If the email exists and is not verified, a verification email has been sent.",
    }


@router.get("/user/verify-email")
async def confirm_email_verification(token: str = Query(..., min_length=20)):
    """使用驗證連結中的一次性 token 完成信箱驗證。"""

    ensure_auth_schema()
    verify_email_token(token)
    return {"status": "success", "message": "Email verified successfully."}


@router.post("/user/forgot-password")
async def forgot_password(payload: ForgotPasswordRequest):
    """寄送一次性重設密碼連結與 token。"""

    ensure_auth_schema()
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT user_id, username, email
                FROM user
                WHERE email = %s
                """,
                (payload.email,),
            )
            db_user = cursor.fetchone()
    finally:
        conn.close()

    if db_user:
        try:
            send_password_reset_email(db_user["user_id"], db_user["username"], db_user["email"])
        except Exception:
            # 忘記密碼也採固定回應，避免暴露帳號存在性與寄信失敗細節。
            pass

    return {
        "status": "success",
        "message": "If the email exists, a password reset link has been sent.",
    }


@router.post("/user/reset-password")
async def reset_password(payload: ResetPasswordRequest):
    """使用一次性 token 重設密碼。"""

    ensure_auth_schema()
    if payload.new_password != payload.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match.")

    token_record = consume_password_reset_token(payload.token)
    new_password_hash = pwd_context.hash(payload.new_password)
    update_password(token_record["user_id"], new_password_hash)

    return {"status": "success", "message": "Password has been reset successfully."}