from google import genai
import os
from PIL import Image
from dotenv import load_dotenv
import pymysql
import json
import google.api_core.exceptions
from db_utils import get_or_create_id, get_crop_id_by_name,get_db_connection

load_dotenv()

client = genai.Client(api_key=os.getenv("Gemini_API_KEY"))

def get_standard_names():
    conn = get_db_connection()

    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT disease_name FROM disease")
            diseases = [row["disease_name"] for row in cursor.fetchall()]
            cursor.execute("SELECT pest_name FROM pests")
            pests = [row["pest_name"] for row in cursor.fetchall()]
            return diseases, pests
    finally:
        conn.close()



def diagnostic_plant(image_path):
    diseases, pests = get_standard_names()
    disease_list_str = ", ".join(diseases)
    pest_list_str = ", ".join(pests)
    img = Image.open(image_path)

    prompt = f"""
    請分析這張植物照片，你的 "status_name" 欄位必須優先匹配以下清單。
    
    已知疾病清單：{disease_list_str}
    已知蟲害清單：{pest_list_str}
    
    如果完全不符合，請自行生成精確名稱，並嚴格按照以下 JSON 格式回傳（不要包含額外文字）：
    {{
    "crop_name":"植物名稱(中文名)",
    "category": "Healthy/Disease/Pest",
    "status_name": "病名或蟲害簡稱(若健康則填Healthy)",
    "confidence": "準確率(0~1)",
    "suggestion": "發生了甚麼",
    "treatment" : "和建議如何改善"
    }}
    注意:suggestion 請精簡在20字左右。
    """
    try:
        response = client.models.generate_content(model="gemini-2.5-flash",contents=[prompt,img])
        clean_text=response.text.replace('```json', '').replace('```', '').strip()
        return json.loads(clean_text)
    except Exception as e:
        print(f"AI 辨識出錯: {e}")
        return None




def save_to_db(data, image_path,user_id,user_note=""):
    print("--- 開始執行儲存流程 ---") # 加入這行

    crop_name = data.get("crop_name")
    target_crop_id = get_crop_id_by_name(crop_name)
    if target_crop_id is None:
        print("無法關聯植物，儲存失敗。")
        
    category = data.get('category')
    status_name = data.get("status_name")
    disease_id = None
    pest_id = None
    final_suggestion = data.get("suggestion") # 預設用 AI 給的
    final_treatment = data.get("treatment")   # 預設用 AI 給的
    
    
    conn = pymysql.connect(
        user = os.getenv("DB_USER"),
        password = os.getenv("DB_PASSWORD"),
        host = os.getenv("DB_HOST"),
        database = os.getenv("DB_NAME"),
        cursorclass=pymysql.cursors.DictCursor
    )
    try:
        with conn.cursor() as cursor:
            if category == "Disease":
                check_sql = "SELECT disease_id, description, treatment FROM disease WHERE disease_name = %s OR disease_name LIKE %s"
                cursor.execute(check_sql, (status_name,f"%{status_name}%"))
                db_disease = cursor.fetchone()

                if db_disease:
                    # 找到了！使用知識庫裡的專業內容
                    disease_id = db_disease['disease_id']
                    final_suggestion = db_disease['description']
                    final_treatment = db_disease['treatment']
                    print(f"🎯 精確匹配到知識庫條目: {status_name}")
                else:
                    # 沒找到，才呼叫你原本的 get_or_create_id (建立新條目)
                    disease_id = get_or_create_id("disease", status_name, target_crop_id, final_suggestion, final_treatment)
            
            # --- 第二步：如果是 Pest ---
            elif category == 'Pest':
                # ### 關鍵：新增 Pest 的精確匹配 ###
                check_pest_sql = "SELECT pest_id, description, treatment FROM pests WHERE pest_name = %s OR pest_name LIKE %s"
                cursor.execute(check_pest_sql, (status_name,f"%{status_name}%"))
                db_pest = cursor.fetchone()

                if db_pest:
                    pest_id = db_pest['pest_id']
                    final_suggestion = db_pest['description']
                    final_treatment = db_pest['treatment']
                    print(f"🎯 匹配到 Pest 知識庫: {status_name}")
                else:
                    pest_id = get_or_create_id('pests', status_name, target_crop_id, final_suggestion, final_treatment)
            
            sql = """
            INSERT INTO plant_diary (user_id,crop_id,status_name,image_url,disease_id, pest_id,confidence,suggestion,treatment,user_note,created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s,%s, %s,%s, NOW())
            """
            cursor.execute(sql,(
                user_id,target_crop_id,status_name,image_path,disease_id, pest_id,data["confidence"],final_suggestion,final_treatment,user_note))
        conn.commit()
        print(f"✅ 成功！已關聯 {category} ID: {disease_id or pest_id}")
        print("資料已成功存入資料庫!")
        return target_crop_id
    except google.api_core.exceptions.ResourceExhausted:
        return "ERROR: API 配額已達上限（請稍後再試）"
    except Exception as e:
        return f"ERROR: 發生未知錯誤: {str(e)}"
    finally:
        conn.close()

#if __name__ == "__main__":
 #   result = diagnostic_plant(r"")
  #  print(result)
   # save_to_db(result, r"")
