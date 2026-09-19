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


def _coerce_confidence(value) -> float:
    """Keep confidence in a predictable 0.0-1.0 range."""

    try:
        confidence = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, confidence))


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


def diagnostic_plant(image_path):
    """
    分析圖片並回傳 AI 模型最原始的、未經驗證的結構化 JSON。
    這個函式現在只專注於與 AI 溝通。
    """
    img = Image.open(image_path)

    # --- RAG 整合開始 ---
    # 1. 初步分析圖片，產生搜尋查詢
    preliminary_prompt = "You are an agricultural expert. Briefly describe the main subject and any visible symptoms in this image in a few keywords (e.g., 'tomato, leaf spots, yellowing'). This will be used to search a knowledge base. Respond in Traditional Chinese."
    try:
        preliminary_response = client.models.generate_content(model="gemini-2.5-flash", contents=[preliminary_prompt, img])
        search_query = (preliminary_response.text or "").strip()
        print(f"🔍 RAG: 初步分析關鍵詞: '{search_query}'")
    except Exception as e:
        print(f"⚠️ RAG: 初步分析失敗: {e}")
        search_query = "植物病徵" # 使用通用關鍵詞作為備用

    # 2. 搜尋知識庫
    retrieved_context = rag.search_knowledge_base(search_query, k=3)
    # --- RAG 整合結束 ---

    prompt = f"""
    You are a top-tier plant pathologist. Analyze the provided image and context from our knowledge base to provide a professional diagnosis.

    --- Knowledge Base Context ---
    {retrieved_context if retrieved_context else "No specific context found."}
    ---

    Your primary goal is to identify the plant and its condition (disease, pest, or healthy).
    Then, provide a detailed description (suggestion) and actionable treatment steps.
    Finally, classify the issue as 'disease', 'pest', or 'healthy'.

    IMPORTANT:
    - All text MUST be in Traditional Chinese.
    - Standardize the crop and issue names to their most common and correct form.
    - Respond in a valid, non-nested, single-level JSON format.

    JSON Output Structure:
    {{
      "crop_name": "string (標準化的作物名稱)",
      "status_name": "string (標準化的病害/害蟲名稱，或 '健康')",
      "category": "string (One of 'disease', 'pest', 'healthy')",
      "confidence": "float (A value between 0.0 and 1.0)",
      "suggestion": "string (A bulleted list of 2-3 key visual symptoms, using '-' for each point and '\\n' for new lines. Example: '- 葉片有黃斑\\n- 葉緣焦枯')",
      "treatment": "string (A numbered list of actionable steps using '1.', '2.', etc., and '\\n' for new lines. Example: '1. 移除受感染的葉片\\n2. 增加通風')"
    }}
    """
    try:
        response = client.models.generate_content(model="gemini-2.5-flash", contents=[prompt, img])
        clean_text = (response.text or "").replace("```json", "").replace("```", "").strip()
        return json.loads(clean_text)
    except (json.JSONDecodeError, Exception) as e:
        print(f"❌ AI 診斷或 JSON 解析失敗: {str(e)}")
        return None


def _get_standardized_name(new_name: str, existing_names: list[str]) -> str:
    """使用 AI 的語意理解能力來解析同義詞，並回傳一個標準化的名稱。"""
    if not existing_names or new_name in existing_names:
        return new_name

    # 將現有名稱格式化成一個易於閱讀的列表
    existing_names_str = ", ".join([f"'{name}'" for name in existing_names])

    prompt = f"""
    You are a database administrator specializing in agriculture.
    A new diagnosis term is '{new_name}'.
    For this crop, the database already contains the following terms: {existing_names_str}.

    Task: Determine if '{new_name}' is a synonym for one of the existing terms.
    - If it IS a synonym, respond with the EXISTING term from the list.
    - If it is NOT a synonym and represents a genuinely new condition, respond with the NEW term '{new_name}'.

    Your response must be ONLY ONE of the terms.
    """
    try:
        response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        standardized_name = (response.text or "").strip()
        
        # 安全性檢查：確保 AI 的回應是有效的選項之一
        valid_options = existing_names + [new_name]
        if standardized_name in valid_options:
            if standardized_name != new_name:
                print(f"🔬 名稱標準化: '{new_name}' -> '{standardized_name}'")
            return standardized_name
        else:
            # 如果 AI 回應了意外的內容，則退回使用新名稱
            print(f"⚠️ 標準化回退: AI 回應 '{standardized_name}' 無效，使用原名稱 '{new_name}'")
            return new_name
            
    except Exception as e:
        print(f"❌ 標準化失敗: {e}，將使用原名稱 '{new_name}'")
        return new_name


def process_and_update_diagnosis(raw_ai_data: dict, db: Session) -> dict:
    """
    新流程的核心：接收原始 AI 結果，與資料庫交叉比對，然後更新或新增記錄。
    最終永遠以 AI 的最新建議為準。
    """
    if not isinstance(raw_ai_data, dict):
        return _uncertain_diagnosis()

    # 從原始 AI 資料中提取資訊
    crop_name = raw_ai_data.get("crop_name")
    status_name = raw_ai_data.get("status_name")
    category = str(raw_ai_data.get("category", "")).lower()
    confidence = _coerce_confidence(raw_ai_data.get("confidence"))
    ai_suggestion = raw_ai_data.get("suggestion", "AI 未提供建議。")
    ai_treatment = raw_ai_data.get("treatment", "AI 未提供處理方法。")

    # 基本的合理性檢查
    if not all([crop_name, status_name, category]):
        return _uncertain_diagnosis(confidence=confidence)

    # 如果是健康的，直接回傳 AI 結果，不寫入病蟲害資料庫
    if category == "healthy":
        return {
            "crop_name": crop_name,
            "category": "healthy",
            "status_name": HEALTHY_STATUS_NAME,
            "confidence": confidence,
            "suggestion": ai_suggestion,
            "treatment": ai_treatment,
            "grounding_source": "ai_direct_result",
            "requires_review": False,
        }

    # 確定要操作的資料庫模型和欄位
    if category == "disease":
        model_class = models.Disease
        name_column = models.Disease.disease_name
        crop_relation = models.Disease.crop
    elif category == "pest":
        model_class = models.Pest
        name_column = models.Pest.pest_name
        crop_relation = models.Pest.crop
    else:
        return _uncertain_diagnosis(crop_name, confidence)

    # 尋找對應的作物 ID
    crop = db.query(models.Crop).filter(models.Crop.crop_name == crop_name).first()
    if not crop:
        # 如果作物不存在，我們可以選擇在這裡新增它，或回傳不確定
        # 為了簡單起見，我們先回傳不確定
        return _uncertain_diagnosis(crop_name, confidence)

    # --- 名稱標準化流程 ---
    # 1. 取得該作物所有已知的病害/害蟲名稱
    existing_records = db.query(name_column).filter(model_class.crop_id == crop.crop_id).all()
    existing_names = [record[0] for record in existing_records]

    # 2. 呼叫 AI 進行同義詞比對，取得標準化名稱
    standardized_status_name = _get_standardized_name(status_name, existing_names)
    # --- 標準化結束 ---

    # 在對應的病蟲害資料表中查詢記錄 (使用標準化後的名稱)
    record = db.query(model_class).filter(name_column == standardized_status_name, model_class.crop_id == crop.crop_id).first()

    if record:
        # 情況 A：找到了！更新記錄
        print(f"🔄 更新資料庫記錄: {crop_name} - {standardized_status_name}")
        record.description = ai_suggestion
        record.treatment = ai_treatment
        db.commit()
    else:
        # 情況 B：沒找到！新增記錄 (使用標準化後的名稱)
        print(f"✨ 新增資料庫記錄: {crop_name} - {standardized_status_name}")
        new_record = model_class(
            crop_id=crop.crop_id,
            description=ai_suggestion,
            treatment=ai_treatment
        )
        # 動態設定名稱欄位
        setattr(new_record, name_column.name, standardized_status_name)
        db.add(new_record)
        db.commit()

    # 無論更新或新增，都回傳以 AI 最新內容為準的結果
    final_result = {
        "crop_name": crop_name,
        "category": category,
        "status_name": standardized_status_name, # 回傳標準化後的名稱
        "confidence": confidence,
        "suggestion": ai_suggestion,
        "treatment": ai_treatment,
        "grounding_source": "ai_updated_database" if record else "ai_created_database",
        "requires_review": False, # 我們信任 AI 的結果
    }
    return final_result


def get_reference_lists(db: Session) -> tuple[list[str], list[str], list[str]]:
    """從既有 Session 讀取模型參考清單。"""

    crops = [c.crop_name for c in db.query(models.Crop).all()]
    diseases = [d.disease_name for d in db.query(models.Disease).all()]
    pests = [p.pest_name for p in db.query(models.Pest).all()]
    return crops, diseases, pests



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