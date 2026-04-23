from fastapi import APIRouter, Depends, HTTPException
from passlib.context import CryptContext

from app.db.session import get_db_connection
from app.schemas.auth import UserLogin, UserRegister
from app.services.auth import create_access_token, get_current_user

router = APIRouter(tags=["auth"])
pwd_context = CryptContext(schemes=["bcrypt"], bcrypt__ident="2b")


@router.post("/users/register")
async def register_user(user: UserRegister):
    """註冊新使用者。"""

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
                INSERT INTO user (username, password_hash, email, full_name)
                VALUES (%s, %s, %s, %s)
                """,
                (user.username, hashed_password, user.email, user.full_name),
            )
            conn.commit()
            return {"status": "success", "message": f"User {user.username} registered."}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Registration failed: {exc}")
    finally:
        conn.close()


@router.post("/user/login")
async def login_user(user: UserLogin):
    """驗證帳密並簽發 JWT。"""

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT user_id, username, password_hash, role FROM user WHERE username = %s",
                (user.username,),
            )
            db_user = cursor.fetchone()
            if not db_user:
                raise HTTPException(status_code=400, detail="Invalid username or password.")
            if not pwd_context.verify(user.password, db_user["password_hash"]):
                raise HTTPException(status_code=400, detail="Invalid username or password.")

            token = create_access_token(
                {
                    "user_id": db_user["user_id"],
                    "username": db_user["username"],
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
async def get_user_profile(current_user: dict = Depends(get_current_user)):
    """取得目前登入者資料。"""

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT username, email, full_name, created_at FROM user WHERE user_id = %s",
                (current_user["user_id"],),
            )
            user_info = cursor.fetchone()
            if not user_info:
                raise HTTPException(status_code=404, detail="User not found.")
            return {"status": "success", "data": user_info}
    finally:
        conn.close()
