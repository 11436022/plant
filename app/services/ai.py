import json
import os
from datetime import datetime
from pathlib import Path

from google import genai
from PIL import Image
from sqlalchemy.orm import Session

from app.db import models
from app.db.session import SessionLocal
from app.services import rag

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

UNKNOWN_CROP_NAME = "未知作物"
UNKNOWN_STATUS_NAME = "無法判定"
HEALTHY_STATUS_NAME = "健康"
MIN_DIAGNOSIS_CONFIDENCE = 0.65
MIN_HEALTHY_CONFIDENCE = 0.85


def _normalize_name(value: str | None) -> str:
    """Normalize names for exact matching without trusting model wording."""

    return "".join(str(value or "").strip().lower().split())


def _match_known_name(value: str | None, known_names: list[str]) -> str | None:
    """Return the canonical database name only when the AI output matches it."""

    normalized_value = _normalize_name(value)
    if not normalized_value:
        return None

    for known_name in known_names:
        if _normalize_name(known_name) == normalized_value:
            return known_name
    return None


def _coerce_confidence(value) -> float:
    """Keep confidence in a predictable 0.0-1.0 range."""

    try:
        confidence = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, confidence))


def _safe_text(value: str | None, fallback: str) -> str:
    """Use fallback text when model output is missing."""

    text = str(value or "").strip()
    return text if text else fallback


def _uncertain_diagnosis(crop_name: str | None = None, confidence: float = 0.0) -> dict:
    """Return a conservative result instead of inventing a diagnosis."""

    return {
        "crop_name": crop_name or UNKNOWN_CROP_NAME,
        "category": "unknown",
        "status_name": UNKNOWN_STATUS_NAME,
        "confidence": min(confidence, 0.5),
        "suggestion": "- 影像特徵不足，無法與目前資料庫中的作物或病蟲害安全對應\n- 建議重新拍攝清晰葉面、莖部與受害區域",
        "treatment": "1. 暫時隔離疑似受害植株並持續觀察。\n2. 補拍清晰照片後重新診斷。\n3. 若症狀持續擴大，請諮詢農業專家或更新知識庫。",
        "grounding_source": "safety_fallback",
        "requires_review": True,
    }


def validate_diagnosis_result(data, crops: list[str], diseases: list[str], pests: list[str]) -> dict:
    """Constrain AI diagnosis to database-backed crop and disease/pest names."""

    if not isinstance(data, dict):
        return _uncertain_diagnosis()

    confidence = _coerce_confidence(data.get("confidence"))
    crop_name = _match_known_name(data.get("crop_name"), crops)
    if not crop_name:
        return _uncertain_diagnosis(confidence=confidence)

    category = str(data.get("category", "")).strip().lower()
    if category == "healthy":
        if confidence < MIN_HEALTHY_CONFIDENCE:
            return _uncertain_diagnosis(crop_name, confidence)
        return {
            "crop_name": crop_name,
            "category": "healthy",
            "status_name": HEALTHY_STATUS_NAME,
            "confidence": confidence,
            "suggestion": _safe_text(
                data.get("suggestion"),
                "- 目前未觀察到明顯病蟲害特徵\n- 建議維持通風、光照與適當澆水",
            ),
            "treatment": _safe_text(
                data.get("treatment"),
                "1. 維持目前照護方式。\n2. 定期觀察葉片正反面是否出現新斑點或蟲害。",
            ),
            "grounding_source": "model_pending_database_check",
            "requires_review": False,
        }

    if confidence < MIN_DIAGNOSIS_CONFIDENCE:
        return _uncertain_diagnosis(crop_name, confidence)

    if category == "disease":
        status_name = _match_known_name(data.get("status_name"), diseases)
    elif category == "pest":
        status_name = _match_known_name(data.get("status_name"), pests)
    else:
        return _uncertain_diagnosis(crop_name, confidence)

    if not status_name:
        return _uncertain_diagnosis(crop_name, confidence)

    return {
        "crop_name": crop_name,
        "category": category,
        "status_name": status_name,
        "confidence": confidence,
        "suggestion": _safe_text(data.get("suggestion"), "- 已比對到資料庫中的病蟲害名稱，請搭配症狀持續觀察。"),
        "treatment": _safe_text(data.get("treatment"), "1. 依資料庫建議處理。\n2. 若症狀擴大，請重新拍攝並再次診斷。"),
        "grounding_source": "model_pending_database_check",
        "requires_review": False,
    }


def ground_diagnosis_in_database(data: dict, db: Session) -> dict:
    """Cross-check crop ownership and replace generated advice with database facts."""

    crop_name = data.get("crop_name")
    confidence = _coerce_confidence(data.get("confidence"))
    crop = db.query(models.Crop).filter(models.Crop.crop_name == crop_name).first()
    if not crop:
        return _uncertain_diagnosis(confidence=confidence)

    category = str(data.get("category", "")).strip().lower()
    if category == "unknown":
        return _uncertain_diagnosis(crop.crop_name, confidence)

    if category == "healthy":
        if confidence < MIN_HEALTHY_CONFIDENCE:
            return _uncertain_diagnosis(crop.crop_name, confidence)
        return {
            "crop_name": crop.crop_name,
            "category": "healthy",
            "status_name": HEALTHY_STATUS_NAME,
            "confidence": confidence,
            "suggestion": "- 目前影像未見資料庫已知病蟲害的明顯特徵",
            "treatment": "1. 維持正常照護\n2. 定期從相同角度拍攝並比較變化",
            "grounding_source": "crop_database",
            "requires_review": False,
        }

    model_class = models.Disease if category == "disease" else models.Pest if category == "pest" else None
    name_column = models.Disease.disease_name if category == "disease" else models.Pest.pest_name if category == "pest" else None
    if model_class is None or name_column is None:
        return _uncertain_diagnosis(crop.crop_name, confidence)

    record = (
        db.query(model_class)
        .filter(name_column == data.get("status_name"), model_class.crop_id == crop.crop_id)
        .first()
    )
    if not record:
        return _uncertain_diagnosis(crop.crop_name, confidence)

    description = str(record.description or "").strip()
    treatment = str(record.treatment or "").strip()
    return {
        "crop_name": crop.crop_name,
        "category": category,
        "status_name": getattr(record, "disease_name" if category == "disease" else "pest_name"),
        "confidence": confidence,
        "suggestion": description or "- 已比對到此作物資料庫中的病蟲害紀錄",
        "treatment": treatment or "1. 資料庫尚無核准處置內容，請諮詢農業專業人員",
        "grounding_source": "disease_database" if category == "disease" else "pest_database",
        "requires_review": not bool(description and treatment),
    }


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

    # --- RAG 整合開始 ---
    # 1. 初步分析圖片，產生搜尋查詢
    preliminary_prompt = "You are an agricultural expert. Briefly describe the main subject and any visible symptoms in this image in a few keywords (e.g., 'tomato, leaf spots, yellowing'). This will be used to search a knowledge base. Respond in Traditional Chinese."
    try:
        preliminary_response = client.models.generate_content(model="gemini-2.5-flash", contents=[preliminary_prompt, img])
        search_query = (preliminary_response.text or "").strip()
        print(f" RAG: 初步分析關鍵詞: '{search_query}'")
    except Exception as e:
        print(f" RAG: 初步分析失敗: {e}")
        search_query = "植物病徵" # 使用通用關鍵詞作為備用

    # 2. 搜尋知識庫
    retrieved_context = rag.search_knowledge_base(search_query, k=3)
    # --- RAG 整合結束 ---


    prompt = f"""
    You are a top-tier plant pathologist. Analyze the provided image and context from our knowledge base to provide a professional diagnosis. Respond in valid JSON format, using Traditional Chinese for all user-facing text.

    --- Knowledge Base Context ---
    {retrieved_context if retrieved_context else "No specific context found."}
    ---

    Reference Lists (for name standardization):
    - Known crops: {crop_list_str}
    - Known diseases: {disease_list_str}
    - Known pests: {pest_list_str}

    Anti-hallucination rules:
    - crop_name must exactly match one item from Known crops. If uncertain, use "未知作物".
    - For category "disease", status_name must exactly match one item from Known diseases.
    - For category "pest", status_name must exactly match one item from Known pests.
    - If the image is unclear, confidence is low, or no exact crop/disease/pest match exists, use category "unknown" and status_name "無法判定".
    - Do not invent crop names, disease names, pest names, pesticide names, dosages, or treatment steps.

    JSON Output Structure:
    {{
      "crop_name": "string (The crop's name in Traditional Chinese)",
      "category": "string (One of 'disease', 'pest', 'healthy', or 'unknown')",
      "status_name": "string (A name from the matching reference list. If healthy, use '健康'. If unknown, use '無法判定')",
      "confidence": "float (A value between 0.0 and 1.0)",
      "suggestion": "string (A bulleted list of 2-3 key visual symptoms, using '-' for each point and '\\n' for new lines. Example: '- 葉片有黃斑\\n- 葉緣焦枯')",
      "treatment": "string (If not healthy, provide a numbered list of actionable steps using '1.', '2.', etc., and '\\n' for new lines. If healthy, provide a positive confirmation like '繼續保持良好照顧。')"
    }}
    """
    try:
        response = client.models.generate_content(model="gemini-2.5-flash", contents=[prompt, img])
        clean_text = (response.text or "").replace("```json", "").replace("```", "").strip()
        return validate_diagnosis_result(json.loads(clean_text), crops, diseases, pests)
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
    target_crop_id = None
    if crop_name and crop_name != UNKNOWN_CROP_NAME:
        crop = db.query(models.Crop).filter(models.Crop.crop_name == crop_name).first()
        target_crop_id = crop.crop_id if crop else None

    category = str(data.get("category", "")).lower()
    status_name = data.get("status_name") or UNKNOWN_STATUS_NAME
    disease_id = None
    pest_id = None

    # 現在，suggestion 和 treatment 直接來自 data，不再被知識庫覆蓋
    final_suggestion = data.get("suggestion")
    final_treatment = data.get("treatment")

    try:
        # 只接受既有資料庫中的病蟲害名稱，避免 AI 幻覺資料被寫入知識庫。
        if category == "disease":
            disease = db.query(models.Disease).filter(models.Disease.disease_name == status_name).first()
            if disease:
                disease_id = disease.disease_id
            else:
                category = "unknown"
                status_name = UNKNOWN_STATUS_NAME
        elif category == "pest":
            pest = db.query(models.Pest).filter(models.Pest.pest_name == status_name).first()
            if pest:
                pest_id = pest.pest_id
            else:
                category = "unknown"
                status_name = UNKNOWN_STATUS_NAME

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
