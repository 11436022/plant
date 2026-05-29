import json
import os
from datetime import datetime
from pathlib import Path

from google import genai
from PIL import Image
from sqlalchemy.orm import Session

from app.db import models
from app.db.session import SessionLocal
from app.services.knowledge import get_or_complete_knowledge

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


def get_standard_names():
    """讀取資料庫中現有的作物、病害與蟲害名稱。"""

    db = SessionLocal()
    try:
        crops = [c.crop_name for c in db.query(models.Crop).all()]
        diseases = [d.disease_name for d in db.query(models.Disease).all()]
        pests = [p.pest_name for p in db.query(models.Pest).all()]
        return crops, diseases, pests
    finally:
        db.close()


def get_reference_lists(db: Session) -> tuple[list[str], list[str], list[str]]:
    """從既有 Session 讀取模型參考清單。"""

    crops = [c.crop_name for c in db.query(models.Crop).all()]
    diseases = [d.disease_name for d in db.query(models.Disease).all()]
    pests = [p.pest_name for p in db.query(models.Pest).all()]
    return crops, diseases, pests


def diagnostic_plant(image_path, crops=None, diseases=None, pests=None):
    """分析圖片並回傳結構化 JSON。"""

    if crops is None or diseases is None or pests is None:
        crops, diseases, pests = get_standard_names()

    crop_list_str = ", ".join(crops) if crops else "unknown"
    disease_list_str = ", ".join(diseases) if diseases else "unknown"
    pest_list_str = ", ".join(pests) if pests else "unknown"
    img = Image.open(image_path)

    prompt = f"""
    Analyze the provided image and respond in valid JSON format, using Traditional Chinese for all user-facing text.

    Reference Lists (for name standardization):
    - Known crops: {crop_list_str}
    - Known diseases: {disease_list_str}
    - Known pests: {pest_list_str}

    JSON Output Structure:
    {{
      "crop_name": "string (The crop's name in Traditional Chinese)",
      "category": "string (One of 'disease', 'pest', or 'healthy')",
      "status_name": "string (The specific name of the status in Traditional Chinese. If healthy, use '健康')",
      "confidence": "float (A value between 0.0 and 1.0)",
      "suggestion": "string (A bulleted list of 2-3 key visual symptoms, using '-' for each point and '\\n' for new lines. Example: '- 葉片有黃斑\\n- 葉緣焦枯')",
      "treatment": "string (If not healthy, provide a numbered list of actionable steps using '1.', '2.', etc., and '\\n' for new lines. If healthy, provide a positive confirmation like '繼續保持良好照顧。')"
    }}
    """
    try:
        response = client.models.generate_content(model="gemini-2.5-flash", contents=[prompt, img])
        clean_text = (response.text or "").replace("```json", "").replace("```", "").strip()
        return json.loads(clean_text)
    except json.JSONDecodeError as e:
        # 當 AI 回應的不是有效的 JSON 時
        print(f"❌ AI 回應格式錯誤: 無法解析 JSON。原始回應: '{clean_text}'. 錯誤: {str(e)}")
        return None
    except Exception as e:
        # 捕捉所有其他錯誤，例如網路問題、API 金鑰問題等
        print(f"❌ AI 診斷服務發生未知錯誤: {str(e)}")
        return None


async def classify_agriculture_term(name: str) -> str:
    """判斷農業狀態名稱屬於病害或蟲害。"""

    prompt = (
        "Classify the following agricultural status name as exactly one of: "
        f"disease, pest, invalid. Input: {name}"
    )
    try:
        response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        result = (response.text or "").strip().lower()
        if result in {"disease", "pest"}:
            return result
    except Exception:
        pass
    return "invalid"

async def check_if_real_crop(name_val: str) -> bool:
    """利用 AI 判斷輸入的字串是否為真實存在的農作物、植物或蔬果。"""
    from app.services.ai import client

    prompt = (
        f"妳是一位專業的農業專家。請問 '{name_val}' 是否為存在的農作物、蔬果或植物名稱？"
        "請只回答 'True','False' "
        
    )

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash", 
            contents=prompt
        )
        # 取得回傳內容並清理空白與大小寫
        ans = response.text.strip().lower()
        return "true" in ans
    except Exception as e:
        # 如果 AI 服務出錯，保險起見我們預設為 True (或者 False，看你的嚴謹度)
        print(f"AI Check Error: {e}")
        return False


async def save_to_db(data, image_path, user_id, user_note, db: Session):
    """將診斷結果寫入 plant_diary。"""

    crop_name = data.get("crop_name")
    crop_info = await get_or_complete_knowledge("crop", crop_name, db)
    target_crop_id = crop_info["id"] if crop_info else None

    category = str(data.get("category", "")).lower()
    status_name = data.get("status_name")
    disease_id = None
    pest_id = None

    # 現在，suggestion 和 treatment 直接來自 data，不再被知識庫覆蓋
    final_suggestion = data.get("suggestion")
    final_treatment = data.get("treatment")

    try:
        # 我們仍然需要查找 disease/pest ID
        if category == "disease":
            knowledge = await get_or_complete_knowledge("disease", status_name, db)
            disease_id = knowledge["id"]
        elif category == "pest":
            knowledge = await get_or_complete_knowledge("pest", status_name, db)
            pest_id = knowledge["id"]

        new_diary = models.PlantDiary()
        new_diary.user_id = user_id
        new_diary.crop_id = target_crop_id
        new_diary.status_name = status_name
        new_diary.image_url = str(Path(image_path).as_posix())
        new_diary.disease_id = disease_id
        new_diary.pest_id = pest_id
        new_diary.confidence = data.get("confidence")

        # 🌟 這裡使用手動賦值，避免建構子屬性名稱混淆
        # 如果您的資料庫欄位是 suggestion，這會正確運作
        new_diary.gemini_suggestion = final_suggestion
        new_diary.gemini_treatment = final_treatment

        new_diary.user_note = user_note
        new_diary.created_at = datetime.now()

        db.add(new_diary)
        db.commit()
        db.refresh(new_diary)
        return new_diary.id
    except Exception as exc:
        db.rollback()
        print(f"CRITICAL DATABASE ERROR: {str(exc)}") # 🌟 這行會把真正的錯誤原因印在後端視窗
        raise RuntimeError(f"Database Save Failed: {exc}") from exc