import google.generativeai as genai
import os
from PIL import Image
from dotenv import load_dotenv
import pymysql
import json
import google.api_core.exceptions
load_dotenv()

genai.configure(api_key=os.getenv("Gemini_API_KEY"))

model = genai.GenerativeModel("gemini-3-flash-preview")

def diagnostic_plant(image_path):
    img = Image.open(image_path)

    prompt = """
    你是一位植物專家.請分析這張照片並回答:
    1.植物名稱
    2.健康狀態(Healthy/Disease/Pest)
    3.簡易建議
    請用JSON格式回傳,例如{"name":"韭菜", "status":"Disease","suggestion":"疑似疑似鏽病，建議剪除病葉"}
    """
    response = model.generate_content([prompt, img])
    return response.text




def save_to_db(plant_data, image_path):

    connection = pymysql.connect(
        host="localhost",
        user="plant",
        password="1234",
        database="plant_db",
        cursorclass=pymysql.cursors.DictCursor
    )

    try:
        with connection.cursor() as cursor:
            clean_json = plant_data.replace('```json', '').replace('```', '').strip()
            data = json.loads(clean_json)

            sql = """
            INSERT INTO plant_diary (user_id,crop_id,image_url,user_note,created_at)
            VALUES (%s, %s, %s, %s, NOW())
            """
            cursor.execute(sql,(1,2,image_path,data["suggestion"]))
        connection.commit()
        print("資料已成功存入資料庫!")
    except google.api_core.exceptions.ResourceExhausted:
        return "ERROR: API 配額已達上限（請稍後再試）"
    except Exception as e:
        return f"ERROR: 發生未知錯誤: {str(e)}"
    finally:
        connection.close()



if __name__ == "__main__":
    result = diagnostic_plant("")
    save_to_db(result, r"")
