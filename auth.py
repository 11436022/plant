from fastapi import   Depends,HTTPException
import jwt
from fastapi.security import HTTPBearer
from db_utils import get_db_connection


# 1. 建立一個 Security 物件
security = HTTPBearer()
# --- 安全設定 ---
secret_key = "your_super_secret_key_here"
algorithm = "HS256"
access_token_expire_minutes = 60 * 24

async def get_current_user(authorization: str= Depends(security)):
    token = authorization.credentials
    print(f"DEBUG: 接收到的 token 是 {token}")
    
    try:
        
        payload = jwt.decode(token, secret_key, algorithms=[algorithm])

        # 從 Token 裡拆出 user_id
        user_id = payload.get("user_id")
        if user_id is None:
            raise HTTPException(status_code=401,detail="無效的 Token")
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                sql = "SELECT user_id, username, role FROM user WHERE user_id = %s"
                cursor.execute(sql,(user_id,))
                user = cursor.fetchone()
                if not user:
                    raise HTTPException(status_code=401,detail="使用者不存在")
                return user
        finally:
            conn.close()
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401,detail="Token 已過期，請重新登入")
    except Exception:
        raise HTTPException(status_code=401,detail="身分驗證失敗")
    
async def verify_admin(current_user: dict = Depends(get_current_user)):
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="權限不足,只有管理人員可以執行操作")
    return current_user
