from fastapi import  Header, Depends,HTTPException
import jwt
from fastapi.security import HTTPBearer



# 1. 建立一個 Security 物件
security = HTTPBearer()
# --- 安全設定 ---
secret_key = "your_super_secret_key_here"
algorithm = "HS256"
access_token_expire_minutes = 60 * 24
# 這個函式會去檢查 Header 裡的 Authorization
async def get_current_user(authorization: str= Depends(security)):
    token = authorization.credentials
    print(f"DEBUG: 接收到的 token 是 {token}")
    
    try:
        
        payload = jwt.decode(token, secret_key, algorithms=[algorithm])

        # 從 Token 裡拆出 user_id
        user_id = payload.get("user_id")
        if user_id is None:
            raise HTTPException(status_code=401,detail="無效的 Token")
        return user_id
    
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401,detail="Token 已過期，請重新登入")
    except Exception:
        raise HTTPException(status_code=401,detail="身分驗證失敗")