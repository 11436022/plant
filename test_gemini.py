from google import genai
import os
from PIL import Image
from dotenv import load_dotenv
import pymysql
import json
import google.api_core.exceptions
from db_utils import get_or_create_id, get_crop_id_by_name

load_dotenv()

client = genai.Client(api_key=os.getenv("Gemini_API_KEY"))


def diagnostic_plant(image_path):
    img = Image.open(image_path)

    prompt = """
    請分析這張植物照片，並嚴格按照以下 JSON 格式回傳（不要包含額外文字）：
    {
    "crop_name":"植物名稱"(中文名),
    "category": "Healthy/Disease/Pest",
    "status_name": "病名或蟲害簡稱(若健康則填Healthy)",
    "confidence": 準確率(0~1),
    "suggestion": "發生了甚麼",
    "treatment" : "和建議如何改善"
    }
    注意:status_name 請精簡只要疾病或害蟲名稱，不要括號。
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
        return
    category = data.get('category')
    print(f"辨識到的類別是: {category}")
    status_name = data.get("status_name")
    disease_id = None
    pest_id = None
    # 在這裡「呼叫」擴充邏輯
    if category == "Disease":
        disease_id = get_or_create_id("disease",status_name,target_crop_id,data.get("suggestion"),data.get("treatment"))
    elif category == 'Pest':
        pest_id = get_or_create_id('pests', status_name, target_crop_id,data.get('suggestion'), data.get('treatment'))

    # 執行最終的 plant_diary 儲存

    conn = pymysql.connect(
        user = os.getenv("DB_USER"),
        password = os.getenv("DB_PASSWORD"),
        host = os.getenv("DB_HOST"),
        database = os.getenv("DB_NAME"),
        cursorclass=pymysql.cursors.DictCursor
    )
    try:
        with conn.cursor() as cursor:
            
            sql = """
            INSERT INTO plant_diary (user_id,crop_id,status_name,image_url,disease_id, pest_id,confidence,suggestion,user_note,created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s,%s, NOW())
            """
            cursor.execute(sql,(
                user_id,target_crop_id,status_name,image_path,disease_id, pest_id,data["confidence"],data["suggestion"],user_note))
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
