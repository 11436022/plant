from google import genai
import os
from PIL import Image
from dotenv import load_dotenv
import pymysql
import json
import google.api_core.exceptions
load_dotenv()

client = genai.Client(api_key=os.getenv("Gemini_API_KEY"))


def diagnostic_plant(image_path):
    img = Image.open(image_path)

    prompt = """
    你是一位植物專家.請分析這張照片並回答:
    1.植物名稱
    2.健康狀態(Healthy/Disease/Pest)
    3.簡易建議
    請用JSON格式回傳,例如{"name":"韭菜", "status":"白化病","suggestion":"疑似疑似鏽病，建議剪除病葉"}
    """
    try:
        response = client.models.generate_content(model="gemini-2.5-flash",contents=[prompt,img])
        clean_text=response.text.replace('```json', '').replace('```', '').strip()
        return json.loads(clean_text)
    except Exception as e:
        print(f"AI 辨識出錯: {e}")
        return None




def save_to_db(data, image_path):

    conn = pymysql.connect(
        host="localhost",
        user="plant",
        password="1234",
        database="plant_db",
        cursorclass=pymysql.cursors.DictCursor
    )

    try:
        with conn.cursor() as cursor:
            
            sql = """
            INSERT INTO plant_diary (user_id,crop_id,image_url,status_name,user_note,created_at)
            VALUES (%s, %s,%s,%s, %s, NOW())
            """
            cursor.execute(sql,(1,2,image_path,data["status"],data["suggestion"]))
        conn.commit()
        print("資料已成功存入資料庫!")
    except google.api_core.exceptions.ResourceExhausted:
        return "ERROR: API 配額已達上限（請稍後再試）"
    except Exception as e:
        return f"ERROR: 發生未知錯誤: {str(e)}"
    finally:
        conn.close()



if __name__ == "__main__":
    result = diagnostic_plant(r"C:\Users\User\OneDrive\Desktop\MyProject\dataset\lettuce_fushan\disease\IMG_13.jpg")
    save_to_db(result, r"C:\Users\User\OneDrive\Desktop\MyProject\dataset\lettuce_fushan\disease\IMG_13.jpg")
