import pymysql
import json
import os
from dotenv import load_dotenv

# 載入 .env 檔案中的環境變數
load_dotenv()

# --- 組態設定 ---
# 從環境變數讀取資料庫連線資訊
DB_HOST = os.getenv("DB_HOST")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")

# GCS 和輸出檔案設定
GCS_BUCKET_NAME = "plant-doctor-training-data-chm"
GCS_IMAGE_FOLDER = "feedback_images" # 儲存圖片的子資料夾
OUTPUT_FILE = "training_data_toy.jsonl" # 輸出玩具資料集的檔名

def get_db_connection():
    """建立並返回資料庫連線。"""
    try:
        conn = pymysql.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            cursorclass=pymysql.cursors.DictCursor,
            charset='utf8mb4'
        )
        print("資料庫連線成功。")
        return conn
    except pymysql.MySQLError as e:
        print(f"資料庫連線失敗: {e}")
        return None

def export_data():
    """從資料庫匯出資料，並為每筆紀錄產生10筆重複的「玩具」訓練資料。"""
    conn = get_db_connection()
    if not conn:
        return

    try:
        with conn.cursor() as cursor:
            sql = """
                SELECT 
                    id, image_url, original_plant_name, original_disease_name,
                    is_plant_error, is_disease_error, corrected_plant_name, corrected_disease_name
                FROM diagnosis_feedback 
                WHERE is_plant_error = 1 OR is_disease_error = 1;
            """
            cursor.execute(sql)
            feedbacks = cursor.fetchall()

        print(f"找到 {len(feedbacks)} 筆原始回饋紀錄。")

        count = 0
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            for feedback in feedbacks:
                final_plant_name = None
                final_disease_name = None

                if feedback["corrected_plant_name"]:
                    final_plant_name = feedback["corrected_plant_name"]
                elif not feedback["is_plant_error"]:
                    final_plant_name = feedback["original_plant_name"]
                
                if not final_plant_name:
                    print(f"跳過紀錄 (ID: {feedback.get('id', 'N/A')})：無法確定正確的植物名稱。")
                    continue

                if feedback["corrected_disease_name"]:
                    final_disease_name = feedback["corrected_disease_name"]
                elif not feedback["is_disease_error"] and feedback["original_disease_name"]:
                    final_disease_name = feedback["original_disease_name"]
                else:
                    final_disease_name = "健康"

                label = f"{final_plant_name}-{final_disease_name}"
                
                if not feedback["image_url"]:
                    continue
                
                # 從原始 image_url 提取原始檔案名稱 (不含副檔名)
                original_filename = feedback["image_url"].split('/')[-1]
                base_filename = original_filename.rsplit('.', 1)[0]

                # 【核心改動】為每一筆紀錄，產生 10 筆指向複本的資料
                for i in range(10):
                    # 建立指向複本的檔名，例如 feedback_abc_0.jpg
                    new_filename = f"{base_filename}_{i}.jpg"
                    
                    # 建立 Vertex AI 需要的 GCS 路徑
                    gcs_uri = f"gs://{GCS_BUCKET_NAME}/{GCS_IMAGE_FOLDER}/{new_filename}"

                    # 建立標準的 JSONL 格式
                    training_line = {
                        "imageGcsUri": gcs_uri,
                        "classificationAnnotation": {
                            "displayName": label
                        }
                    }
                    
                    f.write(json.dumps(training_line, ensure_ascii=False) + '\n')
                    count += 1

        print(f"成功匯出 {count} 筆「玩具」訓練資料到 {OUTPUT_FILE}")

    except pymysql.MySQLError as e:
        print(f"查詢或寫入檔案時發生錯誤: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    print("開始匯出『玩具』訓練資料...")
    export_data()
