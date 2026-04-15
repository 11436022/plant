from google import genai
import os
from PIL import Image
from dotenv import load_dotenv
import pymysql
import json
from db_utils import get_or_complete_knowledge
from sqlalchemy.orm import Session
import models
from datetime import datetime
from database import SessionLocal

load_dotenv()

client = genai.Client(api_key=os.getenv("Gemini_API_KEY"))

def get_standard_names():
    db = SessionLocal() # 開啟一個臨時連線
    try:
        # 1. 抓取所有植物名稱
        crops = [c.crop_name for c in db.query(models.Crop).all()]
        
        # 2. 抓取所有疾病名稱
        diseases = [d.disease_name for d in db.query(models.Disease).all()]
        
        # 3. 抓取所有蟲害名稱
        pests = [p.pest_name for p in db.query(models.Pest).all()]
        
        return crops, diseases, pests # 確保回傳 3 個值
    finally:
        db.close()



def diagnostic_plant(image_path, crops, diseases, pests):
    crops,diseases, pests = get_standard_names()
    crop_list_str = ", ".join(crops)
    disease_list_str = ", ".join(diseases)
    pest_list_str = ", ".join(pests)
    img = Image.open(image_path)

    prompt = f"""
    你的 "crop_name" 必須優先從以下清單中選擇：
    [{crop_list_str}]
    如果圖片中的植物明顯不屬於上述清單，請回傳 "未知"。

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




async def save_to_db(data, image_path,user_id,user_note, db: Session):
    print("--- 開始執行儲存流程 ---") # 加入這行

    crop_name = data.get("crop_name")
    crop_info = await get_or_complete_knowledge("crop", crop_name, db)
    target_crop_id = crop_info["id"] if crop_info else None

    if target_crop_id is None:
        print("無法關聯植物，儲存失敗。")
        
    category = data.get('category', '').lower()
    status_name = data.get("status_name")
    disease_id = None
    pest_id = None
    final_suggestion = data.get("suggestion") # 預設用 AI 給的
    final_treatment = data.get("treatment")   # 預設用 AI 給的
    
    try:
        # --- 第一步：如果是 Disease ---
        if category == "disease":
            # 呼叫智慧函式：先查知識庫，沒有就叫 Gemini 生成
            knowledge = await get_or_complete_knowledge("disease", status_name, db)
            disease_id = knowledge["id"]
            final_suggestion = knowledge["suggestion"]
            final_treatment = knowledge["treatment"]
            print(f"🎯 已連動 Disease 知識庫: {status_name}")

         
        # --- 第二步：如果是 Pest ---
        elif category == 'pest':
            knowledge = await get_or_complete_knowledge("pest", status_name, db)
            pest_id = knowledge["id"]
            final_suggestion = knowledge["suggestion"]
            final_treatment = knowledge["treatment"]
            print(f"🎯 已連動 Pest 知識庫: {status_name}")

        # --- 第三步：新增紀錄到 PlantDiary ---
        new_diary = models.PlantDiary(
            user_id=user_id,
            crop_id=target_crop_id,
            status_name=status_name,
            image_url=str(image_path),
            disease_id=disease_id,
            pest_id=pest_id,
            confidence=data.get("confidence"),
            suggestion=final_suggestion,
            treatment=final_treatment,
            user_note=user_note,
            created_at=datetime.now()
        )

        db.add(new_diary)
        db.commit() # 提交儲存
        db.refresh(new_diary) # 重新整理以取得自動生成的 ID

        print(f"✅ 成功！已存入 PlantDiary ID: {new_diary.id}")
        return target_crop_id

    except Exception as e:
        db.rollback() # 出錯時回滾，確保資料庫一致性
        print(f"❌ ERROR: 發生未知錯誤: {str(e)}")
        return f"ERROR: {str(e)}"

#if __name__ == "__main__":
 #   result = diagnostic_plant(r"")
  #  print(result)
   # save_to_db(result, r"")
