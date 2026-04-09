from fastapi import FastAPI, UploadFile, File, Form, Body,Header, Depends
import shutil
import os
from test_gemini import save_to_db, diagnostic_plant
from fastapi.staticfiles import StaticFiles
from fastapi import HTTPException
from db_utils import get_db_connection
import uvicorn
from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext
import jwt
import datetime
from auth import get_current_user, verify_admin
from pathlib import Path


app = FastAPI(title = "植物病害診斷系統 API")
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
def read_root():
    return {"message": "後端伺服器運作中！請訪問 /docs 查看 API 文件"}

UPLOAD_DIR = Path("static/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
#上傳照片
@app.post("/diaries/upload")
async def create_diary(
    user_note: str = Form(""),
    file: UploadFile = File(...),
    current_user_id: dict = Depends(get_current_user)
):
    user_id = current_user_id["user_id"]
    file_path = UPLOAD_DIR / file.filename

    with open(file_path,"wb") as buffer:
        shutil.copyfileobj(file.file,buffer)
    db_path = file_path.as_posix()
    result = diagnostic_plant(db_path)
    if result:
        
        # 組合出前端可以直接用的網址
        full_url = f"http://127.0.0.1:8000/{file_path.replace(os.sep, '/')}"
        my_id = save_to_db(result, file_path,current_user_id, user_note)
        return {
            "status":"success",
            "message": "紀錄已存入資料庫",
            "data": {
                "crop_id": my_id,
                "user": user_id,
                "category": result.get("category"),
                "status_name": result.get("status_name"),
                "confidence":result.get("confidence"),
                "image_url": full_url, # 回傳完整網址給前端
                "suggestion": result.get("suggestion"),
                "treatment" : result.get("treatment")
            }
        }
    return {"status":"error","message":"AI 辨識失敗"}

@app.get("/diaries")
async def get_all_history(current_user_id:int = Depends(get_current_user)):
    """取得所有診斷歷史紀錄"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            #透過 JOIN 同時抓出作物名稱(crop_name)
            sql = """
            SELECT
                d.id,
                c.crop_name as crop_name,
                d.status_name,
                d.image_url,
                d.created_at
            From plant_diary d
            LEFT JOIN crop c ON d.crop_id = c.crop_id
            Where d.user_id = %s
            ORDER BY d.created_at desc
            """
            cursor.execute(sql,(current_user_id,))
            rows = cursor.fetchall()
            # 修正圖片路徑：讓它變成瀏覽器可以直接點開的網址
            for row in rows:
                if row["image_url"]:
                    # 處理 Windows 路徑斜線問題並補上主機位址
                    clean_path = row["image_url"].replace("\\","/")
                    row["image_url"] = f"http://127.0.0.1:8000/{clean_path}"
            return {"status": "success", "count": len(rows), "data": rows}
    except Exception as e:
        print(f"查詢失敗:{e}")
        raise HTTPException(status_code=500,detail="資料庫查詢失敗")
    finally:
        conn.close()

@app.get("/admin/all-diaries")
async def admin_get_all_diaries(admin: dict = Depends(verify_admin)):
    """管理員可以看到所有使用者的辨識紀錄"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            sql = "SELECT * FROM plant_diary ORDER BY created_at DESC"
            cursor.execute(sql)
            rows = cursor.fetchall()
            return {"status": "success", "total_records": len(rows), "data": rows}
    finally:
        conn.close()

#取得diary中特定的日誌
@app.get("/diaries/{diary_id}")
async def get_diary_detail(diary_id: int, current_user_id: int = Depends(get_current_user)):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
            SELECT d.*, c.crop_name as crop_name
            FROM plant_diary d
            LEFT JOIN crop c ON d.crop_id = c.crop_id
            WHERE d.id = %s AND d.user_id = %s
            """
            cursor.execute(sql,(diary_id,current_user_id))
            detail = cursor.fetchone()
            if not detail:
                raise HTTPException(status_code=404, detail = "找不到此紀錄或您無權查看")
            
            if detail.get("image_url"):
                detail["image_url"] = detail["image_url"].replace("\\","/")
                # 如果是本機測試，這裡可以補上網址前綴
                if not detail['image_url'].startswith("http"):
                    detail['image_url'] = f"http://127.0.0.1:8000/{detail['image_url']}"
                return {"status": "success", "data": detail}
    finally:
        conn.close()

#刪除日誌
@app.delete("/diaries/{diary_id}")
async def delete_diary(diary_id:int,current_user_id: int = Depends(get_current_user)):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT image_url From plant_diary Where id=%s AND user_id = %s",(diary_id,current_user_id))
            record = cursor.fetchone()
            if not record:
                raise HTTPException(status_code=404, detail="找不到該筆紀錄")
            sql = "DELETE From plant_diary Where id = %s"
            cursor.execute(sql,(diary_id,))
            conn.commit()

            image_path = record.get("image_url")
            if image_path and os.path.exists(image_path):
                os.remove(image_path)
                print(f"--- 已成功刪除實體檔案: {image_path} ---")
            return {"status":"success","message":f"ID{diary_id}已成功刪除"}
    except Exception as e:
        print(f"刪除失敗:{e}")
        raise HTTPException(status_code=500,detail=str(e))
    finally:
        conn.close()

# 1. 設定密碼加密工具 (使用 bcrypt 演算法)
pwd_context = CryptContext(schemes=["bcrypt"], bcrypt__ident="2b")

# 2. 定義註冊用的資料格式 (Schema)
class UserRegister(BaseModel):
    username: str
    password: str
    email: EmailStr
    full_name: str = None

#建立帳戶
@app.post("/users/register")
async def register_user(user: UserRegister):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # A. 檢查帳號或 Email 是否已存在
            check_sql = "SELECT user_id From user Where username = %s OR email = %s"
            cursor.execute(check_sql,(user.username,user.email))
            if cursor.fetchone():
                raise HTTPException(status_code=400, detail="帳號或 Email 已被註冊過囉！")
            # B. 密碼加密 (雜湊化)
            hashed_password = pwd_context.hash(user.password)

            insert_sql = """
            INSERT into user (username, password_hash, email, full_name)
            VALUES(%s, %s, %s, %s)
            """
            cursor.execute(insert_sql,(user.username, hashed_password, user.email, user.full_name))
            conn.commit()
            return {"status":"success", "message":f"歡迎 {user.username}！註冊成功。"}
    except Exception as e:
        print(f"註冊出錯:{e}")
        raise HTTPException(status_code=500, detail="伺服器註冊失敗")
    finally:
        conn.close()


# --- 安全設定 ---
secret_key = "your_super_secret_key_here"
algorithm = "HS256"
access_token_expire_minutes = 60 * 24

# 1. 建立登入用的資料格式
class UserLogin(BaseModel):
    username: str
    password: str

#帳戶登入
@app.post("/user/login")
async def login_user(user:UserLogin):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # A. 找尋使用者
            sql = "SELECT user_id, username, password_hash, role FROM user WHERE username = %s"
            cursor.execute(sql,(user.username,))
            db_user = cursor.fetchone()

            if not db_user:
                raise HTTPException(status_code=400, detail="帳號或密碼錯誤 (找不到帳號)")
            # B. 比對密碼 (使用之前的 pwd_context)
            if not pwd_context.verify(user.password, db_user["password_hash"]):
                raise HTTPException(status_code=400, detail="帳號或密碼錯誤 (密碼不對)")
            # C. 密碼正確，產生 JWT Token
            payload = {
                "user_id": db_user["user_id"],
                "username": db_user["username"],
                "role": db_user["role"],
                "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=access_token_expire_minutes)
            }
            token = jwt.encode(payload, secret_key, algorithm=algorithm)

            return {
                "status": "success",
                "message": "登入成功!",
                "access_token": token,
                "token_type": "bearer"
            }
    finally:
        conn.close()

#呼叫這個 API 後，前端就能在側邊欄顯示 使用者的名字及資訊
@app.get("/user/me")
async def get_user_profile(current_user_id: int = Depends(get_current_user)):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            sql = "SELECT username, email, full_name, created_at FROM user WHERE user_id = %s"
            cursor.execute(sql,(current_user_id,))
            user_info = cursor.fetchone()

            if not user_info:
                raise HTTPException(status_code=404, detail="找不到使用者")
            return {"status":"success", "data": user_info}
    finally:
        conn.close()





            
if __name__ == "__main__":
    
    uvicorn.run(app, host="0.0.0.0", port=8000)