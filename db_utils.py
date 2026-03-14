import pymysql 
import os
from dotenv import load_dotenv

load_dotenv()

def get_db_connection():
    return pymysql.connect(
        user = os.getenv("DB_USER"),
        password = os.getenv("DB_PASSWORD"),
        host = os.getenv("DB_HOST"),
        database = os.getenv("DB_NAME"),
        cursorclass=pymysql.cursors.DictCursor
    )

def get_or_create_id(table_name,name_val, target_crop_id,description=None, treatment=None):
    # 1. 定義欄位映射表 (根據你的資料庫實際欄位名稱設定)
    column_mapping = {
        "disease": {"id": "disease_id", "name": "disease_name"},
        "pests": {"id": "pest_id", "name": "pest_name"}
    }
    # 2. 取得當前資料表對應的欄位名稱
    # 如果傳入的 table_name 不在對應表裡，預設使用 'id' 和 'name'
    cols = column_mapping.get(table_name, {"id": "id", "name": "name"})
    id_col = cols["id"]
    name_col = cols["name"]

    """
    檢查名稱是否存在，若無則新增。
    支援同時存入描述與治療建議。
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # 執行查詢
            check_sql = f"SELECT {id_col} FROM {table_name} WHERE {name_col} = %s AND crop_id = %s"
            cursor.execute(check_sql,(name_val,target_crop_id))
            result = cursor.fetchone()
            
            if result:
                return result[id_col]
            
            insert_sql = f"""
                INSERT INTO {table_name} ({name_col},crop_id,description,treatment)
                VALUES(%s,%s,%s,%s)
            """
            cursor.execute(insert_sql,(name_val,target_crop_id,description,treatment))
            conn.commit()
            return cursor.lastrowid
    except Exception as e:
        print(f"資料庫操作失敗: {e}")
        return None
    finally:
        conn.close()

def get_crop_id_by_name(crop_name):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            sql = "SELECT crop_id FROM crop WHERE crop_name = %s"
            cursor.execute(sql, (crop_name,))
            result =  cursor.fetchone()
            if result:
                return result["crop_id"]
            else:
                print(f"⚠️ 警告：crop 表找不到名為 '{crop_name}' 的植物")
                return None
    finally:
        conn.close()