from fastapi import FastAPI, UploadFile, File, Form
import shutil
import os
import uuid
from test_gemini import save_to_db, diagnostic_plant
from fastapi.staticfiles import StaticFiles
from fastapi import HTTPException
from db_utils import get_db_connection
import uvicorn
from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext
import pymysql


app = FastAPI(title = "植物病害診斷系統 API")
app.mount("/static", StaticFiles(directory="static"), name="static")
upload_dir = "static/uploads"
os.makedirs(upload_dir,exist_ok=True)

@app.get("/")
def read_root():
    return {"message": "後端伺服器運作中！請訪問 /docs 查看 API 文件"}

@app.post("/diaries/upload")
async def create_diary(
    user_note: str = Form(""),
    user_id: int = Form(...),
    file: UploadFile = File(...)
):
    # 1. 產生唯一檔名並儲存圖片
    file_extension = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    file_path = os.path.join(upload_dir, unique_filename)

    with open(file_path,"wb") as buffer:
        shutil.copyfileobj(file.file,buffer)

    result = diagnostic_plant(file_path)
    if result:
        
        # 組合出前端可以直接用的網址
        full_url = f"http://127.0.0.1:8000/{file_path.replace(os.sep, '/')}"
        my_id = save_to_db(result, file_path,user_id, user_note)
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
async def get_all_history(user_id:int):
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
                d.confidence,
                d.image_url,
                d.suggestion,
                d.user_note,
                d.created_at
            From plant_diary d
            LEFT JOIN crop c ON d.crop_id = c.crop_id
            Where d.user_id = %s
            ORDER BY d.created_at desc
            """
            cursor.execute(sql,(user_id,))
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

@app.delete("/diaries/{diariy_id}")
async def delete_diary(diary_id:int):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT image_url From plant_diary Where id=%s",(diary_id,))
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



if __name__ == "__main__":
    
    uvicorn.run(app, host="0.0.0.0", port=8000)