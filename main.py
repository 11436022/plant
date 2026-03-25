from fastapi import FastAPI, UploadFile, File, Form
import shutil
import os
import uuid
from test_gemini import save_to_db, diagnostic_plant
from fastapi.staticfiles import StaticFiles
from fastapi import HTTPException
from db_utils import get_db_connection
import uvicorn

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
        my_id = save_to_db(result, file_path, user_note)
        return {
            "status":"success",
            "message": "紀錄已存入資料庫",
            "data": {
                "crop_id": my_id,
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
async def get_all_history():
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
            ORDER BY d.created_at desc
            """
            cursor.execute(sql)
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


if __name__ == "__main__":
    
    uvicorn.run(app, host="0.0.0.0", port=8000)