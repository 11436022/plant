import os
import json
import pymysql
from dotenv import load_dotenv

# 載入 .env 檔案中的環境變數
load_dotenv()

# --- 設定 ---
DB_HOST = os.getenv("DB_HOST")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")
IMAGE_PUBLIC_URL_BASE = os.getenv("IMAGE_PUBLIC_URL_BASE", "http://127.0.0.1:8000")
OUTPUT_FILE = "training_data.jsonl"

def get_db_connection():
    """建立並返回資料庫連線"""
    try:
        conn = pymysql.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            cursorclass=pymysql.cursors.DictCursor
        )
        return conn
    except pymysql.MySQLError as e:
        print(f"資料庫連線失敗: {e}")
        return None

def build_public_image_url(relative_path: str) -> str:
    """將相對路徑轉換為完整的公開 URL"""
    if relative_path.startswith('http'):
        return relative_path
    return f"{IMAGE_PUBLIC_URL_BASE.rstrip('/')}/{relative_path.lstrip('/')}"

def export_data():
    """從資料庫匯出已標註的資料到 JSONL 檔案"""
    conn = get_db_connection()
    if not conn:
        return

    try:
        with conn.cursor() as cursor:
            # 查詢所有經過管理者標註的紀錄
            # 注意：這裡使用資料庫實際存在的欄位名稱
            sql = """
                SELECT 
                    image_url, 
                    corrected_plant_name, 
                    corrected_disease_name
                FROM diagnosis_feedback 
                WHERE 
                    corrected_plant_name IS NOT NULL 
                    OR corrected_disease_name IS NOT NULL;
            """
            cursor.execute(sql)
            feedbacks = cursor.fetchall()

        print(f"找到 {len(feedbacks)} 筆已標註的紀錄。")

        count = 0
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            for feedback in feedbacks:
                # 組合標籤，如果病名為空，則預設為 "健康"
                plant_name = feedback["corrected_plant_name"]
                disease_name = feedback["corrected_disease_name"] or "健康"
                
                # 只有當植物名稱存在時才建立標籤
                if not plant_name:
                    continue

                label = f"{plant_name}-{disease_name}"
                
                # 建立完整的圖片 URL
                image_url = build_public_image_url(feedback["image_url"])

                # 建立 JSON 物件並寫入檔案
                record = {
                    "image_url": image_url,
                    "correct_label": label
                }
                f.write(json.dumps(record, ensure_ascii=False) + '\n')
                count += 1

        print(f"成功匯出 {count} 筆訓練資料到 {OUTPUT_FILE}")

    except pymysql.MySQLError as e:
        print(f"查詢或寫入檔案時發生錯誤: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    print("開始匯出訓練資料...")
    export_data()