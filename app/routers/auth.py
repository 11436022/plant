from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.db.session import get_db
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
    issue_email_verification,
    send_password_reset_email,
    update_password,
    verify_email_token,
)
from app.services.auth import create_access_token, get_current_user

router = APIRouter(tags=["auth"])
pwd_context = CryptContext(schemes=["bcrypt"], bcrypt__ident="2b")


# --- CRUD輔助函數 ---
def get_user_by_email(db: Session, email: str) -> User | None:
    """透過信箱查詢使用者。"""
    return db.query(User).filter(User.email == email).first()


def get_user_by_username(db: Session, username: str) -> User | None:
    """透過使用者名稱查詢使用者。"""
    return db.query(User).filter(User.username == username).first()


def get_user_by_username_or_email(db: Session, username: str, email: str) -> User | None:
    """透過使用者名稱或信箱查詢使用者。"""
    return db.query(User).filter((User.username == username) | (User.email == email)).first()


def create_user(db: Session, user: UserRegister) -> User:
    """使用 ORM 建立新使用者。"""
    hashed_password = pwd_context.hash(user.password)
    db_user = User(
        username=user.username,
        password_hash=hashed_password,
        email=user.email,
        full_name=user.full_name,
        is_email_verified=False,  # 新註冊使用者預設為未驗證
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


@router.post("/users/register")
async def register_user(user: UserRegister, db: Session = Depends(get_db)):
    """使用 ORM 建立帳號，並寄出信箱驗證信。"""
    db_user = get_user_by_username_or_email(db, username=user.username, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Username or email already exists.")

    try:
        new_user = create_user(db, user)
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Registration failed: {exc}")

    # 註冊成功後寄送驗證信
    email_sent = True
    warning = None
    try:
        # 注意： issue_email_verification 現在也需要 db session
        issue_email_verification(new_user.user_id, new_user.username, new_user.email, db=db)
    except Exception as exc:
                print(f"[EMAIL SEND FAILED]: {exc}") # 印出詳細錯誤
                email_sent = False
                warning = str(exc)

    return {
        "status": "success",
        "message": f"User {user.username} registered.",
        "user_id": new_user.user_id,
        "verification_required": True,
        "email_sent": email_sent,
        "warning": warning,
    }


@router.post("/login")
async def login_user(
    db: Session = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()
):
    """使用 ORM 登入帳號，未驗證信箱者不可取得 JWT。"""
    db_user = get_user_by_username(db, username=form_data.username)

    if not db_user:
        raise HTTPException(status_code=400, detail="Invalid username or password.")
    if not pwd_context.verify(form_data.password, db_user.password_hash):
        raise HTTPException(status_code=400, detail="Invalid username or password.")
    if not db_user.is_email_verified:
        raise HTTPException(
            status_code=403,
            detail="Email not verified. Please verify your email before logging in.",
        )

    token = create_access_token(
        {
            "sub": db_user.username,
            "user_id": db_user.user_id,
            "role": db_user.role,
        }
    )
    return {
        "status": "success",
        "message": "Login successful.",
        "access_token": token,
        "token_type": "bearer",
        "email": db_user.email,
    }


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
async def request_email_verification(
    payload: EmailVerificationRequest, db: Session = Depends(get_db)
):
    """補寄驗證信；回應固定化，避免直接暴露帳號是否存在。"""
    db_user = get_user_by_email(db, email=payload.email)

    if db_user and not db_user.is_email_verified:
        try:
            # 呼叫已重構的服務，傳入 db session
            issue_email_verification(db_user.user_id, db_user.username, db_user.email, db)
        except Exception as exc:
            print(f"[RE-SEND EMAIL FAILED]: {exc}") # 印出詳細錯誤
            # 補寄端點維持通用成功回應，避免成為探測信箱存在性的工具。
            pass

    return {
        "status": "success",
        "message": "If the email exists and is not verified, a verification email has been sent.",
    }


@router.get("/user/verify-email")
async def confirm_email_verification(
    token: str = Query(..., min_length=20), db: Session = Depends(get_db)
):
    """使用驗證連結中的一次性 token 完成信箱驗證。"""
    verify_email_token(token, db)
    return {"status": "success", "message": "Email verified successfully."}


@router.post("/user/forgot-password")
async def forgot_password(payload: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """寄送一次性重設密碼連結與 token。"""
    db_user = get_user_by_email(db, email=payload.email)

    if db_user:
        try:
            # 呼叫已重構的服務，傳入 db session
            send_password_reset_email(db_user.user_id, db_user.username, db_user.email, db)
        except Exception:
            # 忘記密碼也採固定回應，避免暴露帳號存在性與寄信失敗細節。
            pass

    return {"status": "success", "message": "If the email exists, a password reset link has been sent."}


@router.get("/app-redirect")
async def app_redirect(target: str = Query(...), token: str = Query(...)):
    """將 HTTP 連結重新導向至 App 的深層連結。"""
    final_url = f"{target}?token={token}"
    return RedirectResponse(url=final_url)


@router.post("/user/reset-password")
async def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    """使用一次性 token 重設密碼。"""
    if payload.new_password != payload.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match.")

    token_record = consume_password_reset_token(payload.token, db)
    new_password_hash = pwd_context.hash(payload.new_password)
    update_password(token_record.user_id, new_password_hash, db)

    return {"status": "success", "message": "Password has been reset successfully."}