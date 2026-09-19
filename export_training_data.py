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
GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME", "plant-doctor-training-data-chm")
GCS_IMAGE_FOLDER = "feedback_images" # 新增：定義 GCS 中的子資料夾
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

def export_data():
    """從資料庫匯出已標註的資料到 JSONL 檔案，採用更智能的標籤邏輯。"""
    conn = get_db_connection()
    if not conn:
        return

    try:
        with conn.cursor() as cursor:
            # 查詢所有使用者標記為錯誤的，或管理者已經標註過的紀錄
            # 這次我們把所有相關欄位都拿出來，讓 Python 做更細緻的判斷
            sql = """
                SELECT 
                    id,
                    image_url,
                    original_plant_name,
                    original_disease_name,
                    is_plant_error,
                    is_disease_error,
                    corrected_plant_name,
                    corrected_disease_name
                FROM diagnosis_feedback 
                WHERE 
                    is_plant_error = 1
                    OR is_disease_error = 1;
            """
            cursor.execute(sql)
            feedbacks = cursor.fetchall()

        print(f"找到 {len(feedbacks)} 筆潛在的訓練資料。")

        count = 0
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            for feedback in feedbacks:
                # --- 全新的智慧標籤邏輯 ---
                final_plant_name = None
                final_disease_name = None

                # 1. 決定最終的植物名稱
                if feedback["corrected_plant_name"]:
                    # 優先級 1：管理者填寫的永遠是最終答案
                    final_plant_name = feedback["corrected_plant_name"]
                elif not feedback["is_plant_error"]:
                    # 優先級 2：如果管理者沒填，但使用者認為植物名沒錯，就採用原始名稱
                    final_plant_name = feedback["original_plant_name"]
                
                # 如果經過以上判斷，還是沒有植物名，那這筆資料就無法使用，跳過
                if not final_plant_name:
                    print(f"跳過紀錄 (ID: {feedback.get('id', 'N/A')})：無法確定正確的植物名稱。")
                    continue

                # 2. 決定最終的病害名稱
                if feedback["corrected_disease_name"]:
                    # 優先級 1：管理者填寫的病名是最終答案
                    final_disease_name = feedback["corrected_disease_name"]
                elif not feedback["is_disease_error"] and feedback["original_disease_name"]:
                     # 優先級 2：如果管理者沒填，但使用者認為病名沒錯，採用原始病名
                    final_disease_name = feedback["original_disease_name"]
                else:
                    # 優先級 3：如果以上條件都不滿足（例如管理者和使用者都沒提供正確病名），
                    # 我們做出一個合理的假設：它可能是一個健康的植物。
                    final_disease_name = "健康"

                # 組合最終標籤
                label = f"{final_plant_name}-{final_disease_name}"
                
                # 從 image_url (e.g., 'static/feedback_uploads/feedback_abc.jpg') 提取檔案名稱
                if not feedback["image_url"]:
                    continue
                filename = feedback["image_url"].split('/')[-1]

                # 建立 Vertex AI 需要的 GCS 路徑 (包含子資料夾)
                gcs_uri = f"gs://{GCS_BUCKET_NAME}/{GCS_IMAGE_FOLDER}/{filename}"

                # 建立 Vertex AI Image Classification 所需的標準 JSONL 格式
                training_line = {
                    "imageGcsUri": gcs_uri,
                    "classificationAnnotation": {
                        "displayName": label
                    }
                }
                
                # 將字典轉換為 JSON 字串並寫入檔案
                f.write(json.dumps(training_line, ensure_ascii=False) + '\n')
                count += 1

        print(f"成功匯出 {count} 筆訓練資料到 {OUTPUT_FILE}")

    except pymysql.MySQLError as e:
        print(f"查詢或寫入檔案時發生錯誤: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    print("開始匯出訓練資料...")
    export_data()