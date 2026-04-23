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
Identify the crop and health status from this image.
只有suggestion/treatment中文回答
Known crops: {crop_list_str}
Known diseases: {disease_list_str}
Known pests: {pest_list_str}

Return valid JSON only:
{{
  "crop_name": "string",
  "category": "Healthy|Disease|Pest",
  "status_name": "string",(若健康則填Healthy)
  "confidence": 0.0,
  "suggestion": "string",
  "treatment": "string"
}}
"""
    try:
        response = client.models.generate_content(model="gemini-2.5-flash", contents=[prompt, img])
        clean_text = (response.text or "").replace("```json", "").replace("```", "").strip()
        return json.loads(clean_text)
    except Exception:
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


async def save_to_db(data, image_path, user_id, user_note, db: Session):
    """將診斷結果寫入 plant_diary。"""

    crop_name = data.get("crop_name")
    crop_info = await get_or_complete_knowledge("crop", crop_name, db)
    target_crop_id = crop_info["id"] if crop_info else None

    category = str(data.get("category", "")).lower()
    status_name = data.get("status_name")
    disease_id = None
    pest_id = None
    final_suggestion = data.get("suggestion")
    final_treatment = data.get("treatment")

    try:
        if category == "disease":
            knowledge = await get_or_complete_knowledge("disease", status_name, db)
            disease_id = knowledge["id"]
            final_suggestion = knowledge["suggestion"]
            final_treatment = knowledge["treatment"]
        elif category == "pest":
            knowledge = await get_or_complete_knowledge("pest", status_name, db)
            pest_id = knowledge["id"]
            final_suggestion = knowledge["suggestion"]
            final_treatment = knowledge["treatment"]

        new_diary = models.PlantDiary(
            user_id=user_id,
            crop_id=target_crop_id,
            status_name=status_name,
            image_url=str(Path(image_path).as_posix()),
            disease_id=disease_id,
            pest_id=pest_id,
            confidence=data.get("confidence"),
            suggestion=final_suggestion,
            treatment=final_treatment,
            user_note=user_note,
            created_at=datetime.now(),
        )

        db.add(new_diary)
        db.commit()
        db.refresh(new_diary)
        return new_diary.id
    except Exception as exc:
        db.rollback()
        raise RuntimeError(f"Failed to save diary: {exc}") from exc
