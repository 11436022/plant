import base64
import json
import math
import os
from datetime import datetime
from pathlib import Path

from google import genai
from PIL import Image
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db import models
from app.db.session import SessionLocal
from app.services import rag
from app.services.convnext import predict_convnext_fast_screen

def get_gemini_client():
    api_key = getattr(settings, "GEMINI_API_KEY", None) or os.getenv("GEMINI_API_KEY")
    return genai.Client(api_key=api_key)


client = get_gemini_client()

UNKNOWN_CROP_NAME = "未知作物"
UNKNOWN_STATUS_NAME = "無法判定"
HEALTHY_STATUS_NAME = "健康"
MIN_DIAGNOSIS_CONFIDENCE = 0.65
MIN_HEALTHY_CONFIDENCE = 0.85

UNKNOWN_CROP_NAMES = {
    "未知作物", "未知", "未知植物", "無法辨識", "無法判定",
    "非植物", "無植物特徵", "非植物影像", "無效影像", "無效",
    "其他", "其他作物", "其他果樹", "其他植物", "未指定", "未選擇", "無", "不確定",
    "unknown", "none"
}
UNKNOWN_STATUS_NAMES = {
    "無法判定", "未知", "無植物特徵", "無病害特徵", "非植物",
    "無法辨識", "無效", "無病徵", "無明顯病徵", "unknown"
}


def call_gemini_with_fallback(
    contents,
    primary_model: str | None = None,
    fallback_models: list[str] | None = None,
    max_retries: int | None = None,
    base_delay: float = 0.8,
):
    """
    呼叫 Gemini API 核心函式，具備 503/429 自適應退避重試機制：
    1. 採用主力模型 (預設 models/gemini-3.8-flash)
    2. 若遇 503 (UNAVAILABLE / high demand) 或 429 暫時性頻率限制，進行短暫退避重試
    3. 若遇 429 專案月度支出上限 (spending cap)，立即終止重試並輸出明確排查指引
    """
    import time

    p_model = primary_model or getattr(settings, "GEMINI_PRIMARY_MODEL", "models/gemini-3.8-flash")
    f_models = fallback_models if fallback_models is not None else getattr(settings, "GEMINI_FALLBACK_MODELS", [])
    retries = max_retries or getattr(settings, "GEMINI_MAX_RETRIES", 2)

    candidate_models = [p_model] + [m for m in f_models if m != p_model]
    last_exception = None

    active_client = client or get_gemini_client()
    try:
        from google.genai import types
        gen_config = types.GenerateContentConfig(temperature=0.0, seed=42)
    except Exception:
        gen_config = None

    for model_name in candidate_models:
        for attempt in range(1, retries + 1):
            try:
                call_kwargs = {"model": model_name, "contents": contents}
                if gen_config is not None:
                    call_kwargs["config"] = gen_config
                response = active_client.models.generate_content(**call_kwargs)
                if response and (response.text is not None):
                    if model_name != p_model:
                        print(f"[OK]  [Gemini 備援成功] 主力模型忙碌，備援模型【{model_name}】順利完成生成。")
                    return response
            except Exception as exc:
                last_exception = exc
                err_msg = str(exc)

                # 專案月度支出上限（專案層級硬性阻擋，非暫時限流，重試無效）
                if "spending cap" in err_msg.lower() or "spend cap" in err_msg.lower():
                    print(
                        f"[Emergency]  [Gemini 專案支出上限] Google Cloud 專案已達月度支出上限 (monthly spending cap)！\n"
                        f"   原因：此限制綁定於 Google Cloud 專案層級，在同一個舊專案中新建 Key 依然會被阻擋。\n"
                        f"   解決：請前往 https://ai.studio/spend 調整上限，或在 https://aistudio.google.com/app/apikey 點擊「Create API key in new project」建立全新專案金鑰。"
                    )
                    raise exc

                is_transient = any(
                    code in err_msg
                    for code in ["503", "429", "UNAVAILABLE", "RESOURCE_EXHAUSTED", "high demand", "overloaded"]
                )
                if is_transient:
                    if attempt < retries:
                        sleep_time = base_delay * attempt
                        print(f"[WARN]  [Gemini 尖峰提醒] {model_name} 暫時忙碌 ({err_msg[:60]}...)，等待 {sleep_time:.1f} 秒後進行第 {attempt + 1} 次重試...")
                        time.sleep(sleep_time)
                        continue
                    else:
                        print(f"[WARN]  [Gemini 自動切換] {model_name} 重試達上限，自動切換至下一備援模型...")
                        break
                else:
                    print(f"[WARN]  [Gemini 異常] {model_name} 回傳錯誤: {err_msg[:80]}...")
                    break

    raise last_exception or RuntimeError("All Gemini candidate models failed to generate content.")



def parse_custom_label(label: str) -> tuple[str, str]:
    """解析客製化標籤 (格式: '植物名稱-病害名稱' 或 '植物名稱-健康')。"""
    if not label or "-" not in label:
        return label or UNKNOWN_CROP_NAME, UNKNOWN_STATUS_NAME
    parts = label.split("-", 1)
    return parts[0].strip(), parts[1].strip()


def _coerce_confidence(value) -> float:
    """Keep confidence in a predictable 0.0-1.0 range."""

    try:
        confidence = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, confidence)) if math.isfinite(confidence) else 0.0


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


def _safe_text(value: str | None, fallback: str) -> str:
    """Use fallback text when model output is missing."""

    text = str(value or "").strip()
    return text if text else fallback


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


def arbitrate_diagnosis(
    gemini_result: dict | None,
    custom_result: dict | None,
    retrieved_rag_context: str = "",
) -> dict:
    """
    後端大法官：三方會診（本地 ConvNeXt 模型、Gemini 多模態、RAG 知識庫）裁決核心。
    處理五大情境：
      1. 雙重命中：Gemini 與客製化模型高度吻合。
      2. 分佈外過濾：Gemini 認出作物，且不在客製化標籤白名單（如草莓），直接捨棄客製化猜測。
      3. 特寫反向救援：Gemini 因特寫判定未知作物，但客製化模型高信心命中專屬標籤，觸發救援。
      4. 病害衝突防禦：同作物但不同病害（如扶桑白化症 vs 扶桑缺鐵症），採納 Gemini，並標記爭議供主動學習。
      5. 安全防禦：雙方皆低分或無法判定，安全煞車並引導重拍。
    """
    if not gemini_result and not custom_result:
        return _uncertain_diagnosis()

    # 提取 Gemini 結果
    gemini_raw_crop = str((gemini_result or {}).get("crop_name", "")).strip()
    gemini_raw_status = str((gemini_result or {}).get("status_name", "")).strip()
    gemini_category = str((gemini_result or {}).get("category", "unknown")).lower()
    gemini_conf = _coerce_confidence((gemini_result or {}).get("confidence", 0.0))
    gemini_sugg = str((gemini_result or {}).get("suggestion", "")).strip()
    gemini_treat = str((gemini_result or {}).get("treatment", "")).strip()

    # 判斷 Gemini 是否認出具體作物
    is_gemini_crop_known = bool(
        gemini_raw_crop and gemini_raw_crop not in [UNKNOWN_CROP_NAME, "未知", "未知植物", "未知作物", "無法判定"]
    )

    # 提取客製化模型結果
    custom_label = (custom_result or {}).get("label", "")
    custom_score = _coerce_confidence((custom_result or {}).get("score", 0.0))
    custom_crop = (custom_result or {}).get("crop_name", "")
    custom_status = (custom_result or {}).get("status_name", "")
    if custom_label and not custom_crop:
        custom_crop, custom_status = parse_custom_label(custom_label)

    # 客製化模型支援之植物清單（動態提取）
    supported_labels = getattr(settings, "CUSTOM_MODEL_DEFAULT_LABELS", ["扶桑-缺鐵症", "扁蒲-健康", "樺木-葉斑病", "樟木-葉斑病"])
    supported_plants = {parse_custom_label(lbl)[0] for lbl in supported_labels}
    custom_min_conf = getattr(settings, "CUSTOM_MODEL_MIN_CONFIDENCE", 0.80)
    custom_rescue_conf = getattr(settings, "CUSTOM_MODEL_RESCUE_CONFIDENCE", 0.85)

    # 情境 1 & 4：Gemini 認出作物，且為客製化支援之作物
    if is_gemini_crop_known and gemini_raw_crop == custom_crop:
        if custom_score >= custom_min_conf:
            # 情境 1：病害吻合或語意接近（雙重命中）
            is_status_match = (
                gemini_raw_status == custom_status
                or (custom_status == HEALTHY_STATUS_NAME and gemini_raw_status == HEALTHY_STATUS_NAME)
                or (custom_status in gemini_raw_status or gemini_raw_status in custom_status)
            )
            if is_status_match:
                final_category = (
                    "healthy" if custom_status == HEALTHY_STATUS_NAME
                    else ("pest" if "蟲" in custom_status else "disease")
                )
                return {
                    "crop_name": custom_crop,
                    "status_name": custom_status,
                    "category": final_category,
                    "confidence": max(gemini_conf, custom_score),
                    "suggestion": gemini_sugg or f"- 專屬模型與通用AI雙重確認：{custom_crop} - {custom_status}",
                    "treatment": gemini_treat or "請依農業專家指示定期防治與觀察。",
                    "grounding_source": "tripartite_verified_custom_hit",
                    "requires_review": False,
                }
            else:
                # 情境 4：同作物但病害衝突（如扶桑白化症 vs 扶桑缺鐵症）
                # 客製化模型受限於閉集 3 標籤，容易誤判相近新病害。
                # 裁決：採納 Gemini 的精細診斷，標記 requires_review=True 作為催生新標籤之依據！
                conflict_note = (
                    f"[WARN]  診斷分歧提醒：通用AI診斷為【{gemini_raw_status}】，專屬模型預測為【{custom_status}】"
                    f"(信心度 {custom_score:.2f})。此案例已標記供後台專家覆核。"
                )
                merged_sugg = f"{conflict_note}\n{gemini_sugg}" if gemini_sugg else conflict_note
                return {
                    "crop_name": gemini_raw_crop,
                    "status_name": gemini_raw_status,
                    "category": gemini_category if gemini_category in ["disease", "pest", "healthy"] else "disease",
                    "confidence": gemini_conf,
                    "suggestion": merged_sugg,
                    "treatment": gemini_treat,
                    "grounding_source": "tripartite_conflict_flagged_for_review",
                    "requires_review": True,
                }
        else:
            # 客製化模型信心不足，採納 Gemini 診斷
            return {
                "crop_name": gemini_raw_crop,
                "status_name": gemini_raw_status,
                "category": gemini_category,
                "confidence": gemini_conf,
                "suggestion": gemini_sugg,
                "treatment": gemini_treat,
                "grounding_source": "gemini_rag_general",
                "requires_review": gemini_conf < MIN_DIAGNOSIS_CONFIDENCE,
            }

    # 情境 2：分佈外已知植物（如草莓、番茄，非客製化模型訓練作物）
    if is_gemini_crop_known and gemini_raw_crop not in supported_plants:
        # 客製化模型完全不認識此作物，其猜測直接捨棄
        return {
            "crop_name": gemini_raw_crop,
            "status_name": gemini_raw_status,
            "category": gemini_category,
            "confidence": gemini_conf,
            "suggestion": gemini_sugg,
            "treatment": gemini_treat,
            "grounding_source": "gemini_rag_ood_custom_discarded",
            "requires_review": gemini_conf < MIN_DIAGNOSIS_CONFIDENCE,
        }

    # 情境 3：Gemini 未認出作物（特寫葉片），但客製化模型高信心（>= 0.85）反向救援
    if not is_gemini_crop_known:
        if custom_result and custom_score >= custom_rescue_conf and custom_crop in supported_plants:
            # 專屬特訓模型救援成功！
            rescue_category = (
                "healthy" if custom_status == HEALTHY_STATUS_NAME
                else ("pest" if "蟲" in custom_status else "disease")
            )
            rescue_sugg = (
                f"[DYNAMIC]  專屬模型反向救援：依病徵特寫高信心 ({custom_score:.2f}) 辨識為【{custom_crop} - {custom_status}】\n"
                f"{gemini_sugg}"
            )
            rescue_treat = gemini_treat or f"請依【{custom_crop} - {custom_status}】標準農業防治手冊處置，注意田間通風與管理。"
            return {
                "crop_name": custom_crop,
                "status_name": custom_status,
                "category": rescue_category,
                "confidence": custom_score,
                "suggestion": rescue_sugg.strip(),
                "treatment": rescue_treat.strip(),
                "grounding_source": "custom_model_reverse_rescue",
                "requires_review": False,
            }

        # 情境 5：兩者皆無法確診，觸發安全防禦煞車
        return _uncertain_diagnosis(
            crop_name=UNKNOWN_CROP_NAME,
            confidence=max(gemini_conf, custom_score)
        )

    # 兜底保險
    if gemini_result:
        return {
            "crop_name": gemini_raw_crop or UNKNOWN_CROP_NAME,
            "status_name": gemini_raw_status or UNKNOWN_STATUS_NAME,
            "category": gemini_category,
            "confidence": gemini_conf,
            "suggestion": gemini_sugg,
            "treatment": gemini_treat,
            "grounding_source": "gemini_fallback",
            "requires_review": True,
        }

    return _uncertain_diagnosis()


def generate_precise_prescription(
    crop_name: str,
    status_name: str,
    category: str = "disease",
    fallback_suggestion: str = "",
    fallback_treatment: str = "",
    db: Session | None = None,
    is_local_convnext_hit: bool = False,
    image_path: str | None = None,
) -> tuple[str, str, str]:
    """
    精準處方箋生成：以 Gemini 親眼看圖的動態處置為核心！
    核心原則：每株植物病症輕重不同（輕微初期、局部中度、嚴重枯萎），
    處置方案必須以 Gemini 針對照片中具體病況的研判為準，不以固定資料庫模板覆蓋。

    優先順序：
    1. Gemini 多模態看圖動態診斷成果 (100% 依據照片中病症輕重度專屬生成)
    2. 若由本地快篩 (ConvNeXt) 命中且無現成處置，調用 Gemini 依照片嚴重度生成客製處置
    3. 離線備援：查詢 MySQL 本地專家資料庫記錄 (作為 AI 無法連線時的保險備援)
    4. 安全通用專家處方 (最底層保險)
    """
    if status_name in UNKNOWN_STATUS_NAMES or crop_name in UNKNOWN_CROP_NAMES or category == "unknown":
        sugg = fallback_suggestion or "- 影像特徵不足或非植物影像，無法進行病理辨識\n- 建議將鏡頭靠近植物葉片或受害部位重新拍攝"
        treat = fallback_treatment or "1. 重新拍攝清晰的植物特寫照片後再次診斷。\n2. 確保光源充足且對焦於葉片或病斑。"
        return sugg, treat, ""

    if status_name in [HEALTHY_STATUS_NAME, "健康"]:
        suggestion = "- 植株生長強健，葉色均勻鮮綠，無枯黃萎凋或異常捲曲變形\n- 葉面及葉背均無明顯病斑、白粉、黴菌或害蟲侵蝕痕跡"
        treatment = "1. 維持當前適度日照與澆水頻率，避免盆土長期積水爛根。\n2. 保持良好通風環境，適時修剪老葉促進通風與生長。\n3. 定期檢查葉背與莖部新芽，持續做好日常田間衛生與預防。"
        return suggestion, treatment, "healthy_status"

    def _is_invalid_text(t: str) -> bool:
        """偵測是否為交白卷或官腔廢話。"""
        if not t or len(t.strip()) < 15:
            return True
        markers = ["未有", "未記載", "知識庫未", "未提供具體", "未有具體", "無法提供"]
        return any(m in t for m in markers)

    # --- 步驟 1：優先查詢 MySQL 官方病蟲害資料庫 (無論本地快篩或雲端兜底，皆優先採用資料庫審定處方) ---
    base_desc = ""
    base_treat_db = ""
    local_db = db
    should_close_db = False
    if local_db is None:
        try:
            from app.db.session import SessionLocal
            local_db = SessionLocal()
            should_close_db = True
        except Exception:
            local_db = None

    if local_db is not None:
        try:
            from app.db import models
            crop_record = local_db.query(models.Crop).filter(models.Crop.crop_name == crop_name).first()
            if crop_record:
                if category == "pest" or "蟲" in status_name:
                    rec = local_db.query(models.Pest).filter(
                        models.Pest.crop_id == crop_record.crop_id,
                        models.Pest.pest_name.like(f"%{status_name}%")
                    ).first()
                else:
                    rec = local_db.query(models.Disease).filter(
                        models.Disease.crop_id == crop_record.crop_id,
                        models.Disease.disease_name.like(f"%{status_name}%")
                    ).first()
                if rec and not _is_invalid_text(rec.description) and not _is_invalid_text(rec.treatment):
                    base_desc = rec.description.strip()
                    base_treat_db = rec.treatment.strip()
        except Exception as db_err:
            print(f"[WARN]  查詢 MySQL 處方資料庫出錯: {db_err}")
        finally:
            if should_close_db and local_db:
                local_db.close()

    if base_desc and base_treat_db:
        if fallback_suggestion and fallback_treatment and not _is_invalid_text(fallback_suggestion) and not _is_invalid_text(fallback_treatment):
            if is_local_convnext_hit or "雙模型會診" in fallback_suggestion:
                print(f"[DYNAMIC]  採用雙模型會診動態處置：依當前照片病徵輕重度專屬生成 -> {crop_name} - {status_name}")
                return fallback_suggestion, fallback_treatment, "convnext_gemini_dynamic_prescription"
        if is_local_convnext_hit:
            convnext_sugg = (
                f"- 【病徵特徵】：{base_desc}\n"
                f"- 【傳播與風險提醒】：請密切檢視鄰近葉片、葉背與植株基部是否出現擴散跡象，高溫多濕或通風不良時病程可能快速加劇。"
            )
            convnext_treat = (
                f"1. 【病部隔離與清除】：立即剪除發病枝葉或受害組織並帶離田間集中銷毀，修剪工具須徹底消毒，阻斷病菌孢子或媒介昆蟲擴散。\n"
                f"2. 【標準防治與用藥處置】：{base_treat_db}\n"
                f"3. 【環境防護管理】：適當拉開植株間距降低微氣候濕度，澆水改採滴灌或盆土注水避免噴濕葉面，發病期暫停施用高氮肥料並保持排水良好。"
            )
            print(f"[ConvNeXt]  本地 ConvNeXt 命中：採用 MySQL 專家資料庫權威處方 -> {crop_name} - {status_name}")
            return convnext_sugg, convnext_treat, "convnext_local_graded_prescription"
        else:
            print(f"[MySQL]  命中 MySQL 專家資料庫標準指引 -> {crop_name} - {status_name}")
            return base_desc, base_treat_db, "mysql_fallback_database"

    # --- 步驟 2：MySQL 資料庫無該病害處方 -> 檢索 FAISS 農業部官方專書並結合 Gemini 動態生成處方 ---
    rag_snippet = ""
    try:
        rag_snippet = rag.search_knowledge_base(f"{crop_name} {status_name}", k=3)
    except Exception:
        rag_snippet = ""

    if image_path and Path(image_path).exists():
        try:
            img = Image.open(image_path)
            rag_ref = f"\n參考農業部官方文獻片段：\n{rag_snippet}\n" if rag_snippet else ""
            rx_prompt = (
                f"你是一位專業植物病理專家。目前已辨識此照片為【{crop_name} - {status_name}】。\n"
                f"{rag_ref}"
                "請根據照片中植株實際病徵嚴重度與官方防治規範，以繁體中文回傳單層 JSON：\n"
                '{"suggestion": "2點具體病徵與風險分析（每點以 - 開頭並以 \\n 換行，每點精簡控制在 30 至 50 字以內）", '
                '"treatment": "3點行動導向防治步驟（以 1. 2. 3. 開頭並以 \\n 換行）。【排版規範】：每點格式為『1. 步驟名稱：具體處置作為與稀釋倍率』，去除冗長理論贅述，每點字數精簡控制在 40 至 60 字以內。"}'
            )
            resp = call_gemini_with_fallback(contents=[rx_prompt, img])
            clean_rx = (resp.text or "").replace("```json", "").replace("```", "").strip()
            rx_data = json.loads(clean_rx)
            gen_sugg = str(rx_data.get("suggestion", "")).strip()
            gen_treat = str(rx_data.get("treatment", "")).strip()
            if not _is_invalid_text(gen_sugg) and not _is_invalid_text(gen_treat):
                print(f"[Gemini]  資料庫無現成處方 -> 已結合 FAISS 農業部專書與 Gemini 動態生成處方：{crop_name} - {status_name}")
                return gen_sugg, gen_treat, "gemini_multimodal_dynamic_prescription"
        except Exception as rx_err:
            print(f"[WARN]  結合 FAISS 與 Gemini 生成處方失敗: {rx_err}")

    if fallback_suggestion and fallback_treatment and not _is_invalid_text(fallback_suggestion) and not _is_invalid_text(fallback_treatment):
        print(f"[DYNAMIC]  採用 Gemini 看圖動態處置：依當前照片病徵輕重度專屬生成 (長度: {len(fallback_suggestion)}/{len(fallback_treatment)})")
        return fallback_suggestion, fallback_treatment, "gemini_multimodal_dynamic_prescription"

    # --- 步驟 3：安全通用專家處方 (離線或雲端異常時之最底層保險) ---
    print(f"[INFO]  使用通用安全農業處方: {crop_name} - {status_name}")
    safe_sugg = (
        f"- 典型病徵：葉面出現【{status_name}】局部色斑、褪綠或水浸狀壞死，請注意受害程度。\n"
        f"- 擴散風險：高溫多濕或通風不良時易向相鄰健康組織蔓延，需即時採取防護。"
    )
    safe_treat = (
        f"1. 病斑修剪隔離：立即剪除發病葉片並集中銷毀，修剪工具消毒，阻斷病原二度感染。\n"
        f"2. 通風控水管理：維持良好通風採光，採盆土注水避免噴濕葉面，發病期間暫停施用氮肥。\n"
        f"3. 推薦保護資材：參照【{crop_name}】植保手冊，於發病初期施用登記核准藥劑或保護型殺菌劑。"
    )
    return safe_sugg, safe_treat, "general_safe_prescription"


def _call_openai_fallback(image_path: str, crop_hint: str | None = None) -> dict | None:
    """跨雲供應商備援：當 Google Gemini 被風控 (403) 或額度超限 (429) 時，由 OpenAI 接棒視覺分析。"""
    openai_key = getattr(settings, "OPENAI_API_KEY", None) or os.getenv("OPENAI_API_KEY")
    if not openai_key:
        return None
    try:
        from openai import OpenAI
        client_oa = OpenAI(api_key=openai_key)
        with open(image_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")

        if crop_hint:
            user_crop_instruction = (
                f"已知使用者指定/選定的作物名稱為：【{crop_hint}】。"
                f"請以該作物為基準，專注鑑別長尾、罕見病徵、生理障礙或害蟲，並回傳精確病害名稱（或判定為 '健康'）。"
            )
        else:
            user_crop_instruction = (
                "請辨識影像中的植物名稱（crop_name）及其健康狀態（status_name，如特定病害、蟲害，或 '健康'）。\n"
                "【關鍵防呆規範】：若影像非植物、純黑、純色、嚴重模糊無特徵、日常非植物用品或手機截圖，"
                "crop_name 必須填寫 '未知作物'，status_name 必須填寫 '無法判定'，category 必須填寫 'unknown'，confidence 填寫 0.0。"
            )

        prompt = f"""
        You are a top-tier plant pathologist.
        {user_crop_instruction}

        IMPORTANT:
        - All text MUST be in Traditional Chinese.
        - Standardize the crop and issue names to their most common and correct form.
        - If the image contains NO plant leaves/organs, or is completely black/invalid/non-plant, category MUST be 'unknown', crop_name MUST be '未知作物', status_name MUST be '無法判定', confidence MUST be 0.0.
        - 若影像中同時出現多種病蟲害跡象（如葉斑、蟲害、焦枯等複合徵候），請以【受害最顯著、最影響植株生長之首要病徵】為唯一確診依據，確保診斷具有高度一致性與決定性。
        - Respond in a valid, non-nested, single-level JSON format.

        JSON Output Structure:
        {{
          "crop_name": "string (標準化的作物名稱，非植物請填 '未知作物')",
          "status_name": "string (標準化的病害/害蟲名稱，健康填 '健康'，非植物請填 '無法判定')",
          "category": "string (One of 'disease', 'pest', 'healthy', 'unknown')",
          "confidence": 0.90,
          "suggestion": "string (2 點核心病徵與風險分析，每點以 '-' 開頭，每點約 30-50 字，'\\n' 換行)",
          "treatment": "string (3 點行動導向防治步驟，以 '1.' '2.' '3.' 開頭，格式為『步驟名稱：具體作法與稀釋倍率』，去除冗長理論贅述，每點精簡控制在 40-60 字以內，'\\n' 換行)"
        }}
        """
        resp = client_oa.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.0,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}
                ]
            }],
            response_format={"type": "json_object"},
            max_tokens=600,
        )
        data = json.loads(resp.choices[0].message.content)
        print(f"[OK]  [跨雲備援成功] Google Gemini 異常，已由 OpenAI gpt-4o-mini 接棒多模態視覺診斷！")
        return data
    except Exception as e:
        print(f"[WARN]  OpenAI 備援兜底失敗: {e}")
        return None


def _call_gemini_fallback(
    image_path: str,
    crop_hint: str | None = None,
    visual_memory_hint: dict | None = None,
    mock_result: dict | None = None,
) -> dict:
    """步驟 3：Gemini 多模態兜底推論 (若失敗自動嘗試 OpenAI 跨雲備援)。"""
    if mock_result is not None:
        return mock_result

    img = Image.open(image_path)
    if visual_memory_hint:
        vm_crop = visual_memory_hint.get("crop_name", "")
        vm_status = visual_memory_hint.get("status_name", "")
        vm_sim = visual_memory_hint.get("similarity", 0.0)
        user_crop_instruction = (
            f"【視覺特徵檢索記憶庫先驗指示】：\n"
            f"本影像與資料庫歷史專家覆核樣本（ID #{visual_memory_hint.get('feedback_id')}）之特徵相似度達 {vm_sim:.1%}！\n"
            f"歷史專家已確認該作物為【{vm_crop}】，病害疑似為【{vm_status}】。\n"
            f"請以此作物【{vm_crop}】為優先先驗依據，專注進行精準病害會診（若特徵明顯非此病害則依看圖診斷實情回傳）。"
        )
    elif crop_hint:
        user_crop_instruction = (
            f"已知使用者指定/選定的作物名稱為：【{crop_hint}】。"
            f"請以該作物為基準，專注鑑別長尾、罕見病徵、生理障礙或害蟲，並回傳精確病害名稱（或判定為 '健康'）。"
            f"若影像特徵嚴重明顯與【{crop_hint}】違背，請依專業視覺判斷修正作物名稱。"
        )
    else:
        user_crop_instruction = (
            "請辨識影像中的植物名稱（crop_name）及其健康狀態（status_name，如特定病害、蟲害，或 '健康'）。\n"
            "【關鍵防呆規範】：若影像非植物、純黑、純色、嚴重模糊無特徵、日常非植物用品或手機截圖，"
            "crop_name 必須填寫 '未知作物'，status_name 必須填寫 '無法判定'，category 必須填寫 'unknown'，confidence 填寫 0.0。"
        )

    prompt = f"""
    You are a top-tier plant pathologist.
    {user_crop_instruction}

    IMPORTANT:
    - All text MUST be in Traditional Chinese.
    - Standardize the crop and issue names to their most common and correct form.
    - If the image contains NO plant leaves/organs, or is completely black/invalid/non-plant, category MUST be 'unknown', crop_name MUST be '未知作物', status_name MUST be '無法判定', confidence MUST be 0.0.
    - 若影像中同時出現多種病蟲害跡象（如葉斑、蟲害、焦枯等複合徵候），請以【受害最顯著、最影響植株生長之首要病徵】為唯一確診依據，確保診斷具有高度一致性與決定性。
    - Respond in a valid, non-nested, single-level JSON format.

    JSON Output Structure:
    {{
      "crop_name": "string (標準化的作物名稱，非植物請填 '未知作物')",
      "status_name": "string (標準化的病害/害蟲名稱，健康填 '健康'，非植物請填 '無法判定')",
      "category": "string (One of 'disease', 'pest', 'healthy', 'unknown')",
      "confidence": "float (A value between 0.0 and 1.0)",
      "suggestion": "string (2 點核心病徵與風險分析，每點以 '-' 開頭，每點約 30-50 字，'\\n' 換行)",
      "treatment": "string (3 點行動導向防治步驟，以 '1.' '2.' '3.' 開頭，格式為『步驟名稱：具體作法與稀釋倍率』，去除冗長理論贅述，每點精簡控制在 40-60 字以內，'\\n' 換行)"
    }}
    """
    try:
        response = call_gemini_with_fallback(contents=[prompt, img])
        clean_text = (response.text or "").replace("```json", "").replace("```", "").strip()
        return json.loads(clean_text)
    except Exception as e:
        print(f"[ERROR]  Gemini 多模態兜底失敗: {e}")
        oa_res = _call_openai_fallback(image_path=image_path, crop_hint=crop_hint)
        if oa_res:
            return oa_res
        return _uncertain_diagnosis(crop_name=crop_hint)


def verify_and_cross_examine_with_gemini(
    image_path: str,
    convnext_hit: dict,
    crop_hint: str | None = None,
    mock_gemini_result: dict | None = None,
) -> dict | None:
    """
    方案 3：軟標籤引導之多模態視覺鑑別診斷與二次覆核 (Cross-Modal Soft-Label Verification)。
    - 不盲目順從 ConvNeXt 監督式標籤！
    - 結合 RAG 知識庫標準病徵描述與 ConvNeXt Top-K 軟標籤分佈。
    - 請 Gemini 檢視照片葉面實際病徵進行「視覺覆核」：
      * 若特徵符合第一候選：確認無誤並開立動態嚴重度處方 (concurred)。
      * 若特徵不符第一候選：直接推翻修正，並記錄推翻依據供後續專家審查與蒸餾 (overruled)。
    """
    if mock_gemini_result is not None:
        return mock_gemini_result

    if not image_path or not Path(image_path).exists():
        return None

    if not getattr(settings, "ENABLE_GEMINI_CROSS_VERIFICATION", True):
        return None

    top_candidates = convnext_hit.get("top_k_candidates") or []
    cand_str_list = []
    for idx, c in enumerate(top_candidates, 1):
        cand_str_list.append(
            f"{idx}. 【{c.get('crop_name')} - {c.get('status_name')}】"
            f"(Softmax機率: {c.get('score', 0):.1%}, 餘弦相似度: {c.get('cosine_similarity', 0):.2f})"
        )
    candidates_text = "\n".join(cand_str_list) if cand_str_list else f"1. 【{convnext_hit.get('crop_name')} - {convnext_hit.get('status_name')}】"

    top1_crop = convnext_hit.get("crop_name", "")
    top1_status = convnext_hit.get("status_name", "")
    cam_ratio = convnext_hit.get("cam_foreground_ratio", 1.0)

    # 檢索 RAG 知識庫中該病害的官方標準視覺特徵
    rag_snippet = ""
    try:
        rag_snippet = rag.search_knowledge_base(f"{top1_crop} {top1_status} 病徵 特徵", k=2)
    except Exception:
        rag_snippet = ""

    rag_text = f"\n【農業部官方標準病徵描述】：\n{rag_snippet}\n" if rag_snippet else ""

    verify_prompt = f"""
你是一位權威資深植物病理學家。
本地輕量級模型（ConvNeXt 監督式快篩）根據影像提出以下軟標籤候選病害（Soft Labels）：
{candidates_text}
（弱監督 CAM 熱力圖前景對齊率：{cam_ratio:.1%}）
{rag_text}
【任務說明】：
請嚴格比對照片中真實植株葉面/組織病徵，進行【視覺特徵二次覆核】：
1. 檢視影像特徵是否確實符合第一候選【{top1_crop} - {top1_status}】之典型病理特徵？
2. 重要原則：請勿盲從第一候選！
   - 若符合第一候選：is_concurred 設為 true，並依照片中實際病斑嚴重度（初期微發/中度擴散/重度壞死）開立專屬動態處置。
   - 若特徵明顯不符第一候選（例如實為第二候選、健康、或未收錄病徵）：請直接將 is_concurred 設為 false，推翻並修正為正確之病名（verified_status），並詳細說明推翻之視覺依據。

請以繁體中文回傳單層 JSON 格式：
{{
  "verified_crop": "{top1_crop}",
  "verified_status": "string (確認或修正後的病害名稱，或 '健康')",
  "category": "string (disease, pest, 或 healthy)",
  "is_concurred": true,
  "confidence": 0.92,
  "suggestion": "string (2 點核心病徵與風險分析，以 '-' 開頭，每點約 30-50 字，'\\n' 換行)",
  "treatment": "string (3 點行動導向防治步驟，以 '1.' '2.' '3.' 開頭，格式為『步驟名稱：具體作法與稀釋倍率』，去除冗長理論贅述，每點精簡控制在 40-60 字以內，'\\n' 換行)"
}}
"""
    try:
        img = Image.open(image_path)
        resp = call_gemini_with_fallback(contents=[verify_prompt, img])
        clean_text = (resp.text or "").replace("```json", "").replace("```", "").strip()
        data = json.loads(clean_text)
        return data
    except Exception as exc:
        print(f"[INFO]  Gemini 多模態二次覆核略過: {exc}")
        return None


def diagnostic_plant(
    image_path: str,
    crops: list[str] | None = None,
    diseases: list[str] | None = None,
    pests: list[str] | None = None,
    crop_hint: str | None = None,
    mock_convnext_result: dict | None = None,
    mock_gemini_result: dict | None = None,
    db: Session | None = None,
    **kwargs,
) -> dict:
    """
    三層瀑布流階層式植物診斷架構 (Three-Tier Cascade Diagnosis Engine):
    步驟 1: 本地模型 (ConvNeXt) 混合學習快篩 (方案 1 CAM 空間對齊 + 方案 2 動態原型 OOD 攔截)
    步驟 2: 方案 3 多模態軟標籤二次覆核 (避免盲信監督式標籤，若未命中則由 Gemini 全域兜底)
    步驟 3: 精準處方箋生成 (優先查庫、過濾 RAG 雜訊、保障高信心成果)
    """
    if crop_hint is None and crops:
        if isinstance(crops, str):
            crop_hint = crops
        elif len(crops) == 1:
            crop_hint = crops[0]

    clean_crop = (
        crop_hint.strip()
        if crop_hint and crop_hint.strip() not in UNKNOWN_CROP_NAMES
        else None
    )

    chosen_crop = None
    chosen_status = None
    chosen_category = "disease"
    chosen_conf = 0.0
    source = "safety_fallback"
    base_sugg = ""
    base_treat = ""

    # 相容舊 mock 參數
    mock_local = mock_convnext_result or kwargs.get("mock_yolo_result")

    # --- 步驟 1：本地模型 (ConvNeXt) 優先快篩 ---
    convnext_hit = predict_convnext_fast_screen(
        image_path=image_path,
        crop_name=clean_crop,
        mock_result=mock_local,
    )
    if convnext_hit and convnext_hit.get("confidence", 0.0) >= settings.CONVNEXT_MIN_CONFIDENCE:
        chosen_crop = convnext_hit["crop_name"]
        chosen_status = convnext_hit["status_name"]
        chosen_category = convnext_hit.get("category", "disease")
        chosen_conf = convnext_hit["confidence"]
        source = "local_convnext_fast_screen"

        # 方案 3：軟標籤引導之多模態視覺二次覆核 (避免盲目採信監督式標籤)
        cross_res = verify_and_cross_examine_with_gemini(
            image_path=image_path,
            convnext_hit=convnext_hit,
            crop_hint=clean_crop,
            mock_gemini_result=mock_gemini_result,
        )
        if cross_res and isinstance(cross_res, dict):
            is_concurred = cross_res.get("is_concurred", True)
            verified_crop = cross_res.get("verified_crop") or chosen_crop
            verified_status = cross_res.get("verified_status") or chosen_status
            verified_cat = cross_res.get("category") or chosen_category
            verified_conf = _coerce_confidence(cross_res.get("confidence", chosen_conf))
            v_sugg = cross_res.get("suggestion", "")
            v_treat = cross_res.get("treatment", "")
            override_reason = cross_res.get("override_reason", "")

            if is_concurred and (verified_status == chosen_status or chosen_status in verified_status):
                source = "convnext_gemini_cross_verified"
                chosen_conf = max(chosen_conf, verified_conf)
                base_sugg = v_sugg
                base_treat = v_treat
                print(f"[Consensus]  [雙模型會診共識] ConvNeXt 與 Gemini 雙重確認標籤無誤：{chosen_crop} - {chosen_status} (信心度: {chosen_conf:.2f})")
            else:
                source = "convnext_overruled_by_gemini_verification"
                chosen_crop = verified_crop
                chosen_status = verified_status
                chosen_category = verified_cat
                chosen_conf = verified_conf
                warning_header = (
                    f"[WARN]  【雙模型會診校正】：本地監督式模型初步猜測為【{convnext_hit['status_name']}】，"
                    f"經多模態專家視覺覆核發現：{override_reason}，已自動校正為【{verified_status}】。"
                )
                base_sugg = f"{warning_header}\n{v_sugg}" if v_sugg else warning_header
                base_treat = v_treat
                print(f"[Override]  [雙模型會診推翻] Gemini 視覺校正 ConvNeXt 標籤：{convnext_hit['status_name']} -> {verified_status} ({override_reason})")
        else:
            if convnext_hit.get("is_confidence_override"):
                print(f"[ConvNeXt]  步驟 1 命中：本地 ConvNeXt 壓倒性信心反轉成功 -> {chosen_crop} - {chosen_status} ({chosen_conf:.2f})")
            else:
                print(f"[ConvNeXt]  步驟 1 命中：本地 ConvNeXt 快篩成功 -> {chosen_crop} - {chosen_status} ({chosen_conf:.2f})")

    # --- 步驟 2：視覺特徵檢索飛輪與 Gemini 多模態兜底 (若步驟 1 未命中) ---
    if not chosen_crop:
        # 方案 2：視覺特徵檢索飛輪 (Visual RAG Memory Flywheel)
        # 若使用者未指定作物，在特徵空間比對歷史專家標註樣本，秒速提供作物先驗知識
        visual_mem_hit = None
        if not clean_crop:
            try:
                from app.services.visual_memory import visual_memory
                visual_mem_hit = visual_memory.search(image_path=image_path, min_similarity=0.82)
                if visual_mem_hit:
                    clean_crop = visual_mem_hit["crop_name"]
                    print(
                        f"[VisualMemory]  [視覺特徵檢索飛輪命中] 匹配歷史專家樣本 #{visual_mem_hit['feedback_id']} "
                        f"(相似度: {visual_mem_hit['similarity']:.2f}) -> 注入作物先驗: 【{clean_crop}】"
                    )
            except Exception as vm_err:
                print(f"[WARN] 視覺記憶檢索異常: {vm_err}")

        print("[Step 2]  步驟 1 本地模型未命中，啟動步驟 2 Gemini 多模態兜底...")
        gemini_res = _call_gemini_fallback(
            image_path=image_path,
            crop_hint=clean_crop,
            visual_memory_hint=visual_mem_hit,
            mock_result=mock_gemini_result,
        )
        gem_crop = str(gemini_res.get("crop_name") or "").strip()
        gem_status = str(gemini_res.get("status_name") or "").strip()
        gem_cat = str(gemini_res.get("category", "")).strip().lower()
        gem_conf = _coerce_confidence(gemini_res.get("confidence", 0.0))

        is_gem_known = bool(
            gem_crop and gem_crop not in UNKNOWN_CROP_NAMES
            and gem_status and gem_status not in UNKNOWN_STATUS_NAMES
            and gem_cat != "unknown"
            and gem_conf >= 0.40
        )

        if is_gem_known or mock_gemini_result is not None:
            chosen_crop = gem_crop or clean_crop or UNKNOWN_CROP_NAME
            chosen_status = gem_status or UNKNOWN_STATUS_NAME
            chosen_category = gem_cat if gem_cat in ["disease", "pest", "healthy"] else "disease"
            chosen_conf = gem_conf
            base_sugg = gemini_res.get("suggestion", "")
            base_treat = gemini_res.get("treatment", "")
            source = "visual_memory_gemini_fallback" if visual_mem_hit else "gemini_multimodal_fallback"
            print(f"[Gemini]  步驟 2 命中：Gemini 多模態兜底完成 -> {chosen_crop} - {chosen_status} ({chosen_conf:.2f})")
        else:
            # 雲端 AI 失敗或回傳未知，嘗試本地 ConvNeXt 極端離線應急（若信心壓倒性高）
            emergency_convnext = predict_convnext_fast_screen(
                image_path=image_path,
                crop_name=None,
                allow_unconstrained_emergency=True,
            )
            if emergency_convnext and emergency_convnext.get("confidence", 0.0) >= settings.CONVNEXT_OVERWHELMING_CONFIDENCE:
                chosen_crop = emergency_convnext["crop_name"]
                chosen_status = emergency_convnext["status_name"]
                chosen_category = emergency_convnext.get("category", "disease")
                chosen_conf = emergency_convnext["confidence"]
                source = "local_convnext_offline_emergency"
                base_sugg = (
                    f"[WARN]  【離線應急救援】：雲端多模態 AI 服務暫時無法連線，"
                    f"由本地離線模型以壓倒性置信度 ({chosen_conf:.1%}) 提供初步應急判定。"
                )
                base_treat = "1. 此為本地離線應急判定，請確認影像無誤。\n2. 待雲端服務恢復後建議重新診斷覆核。"
                print(f"[Emergency]  [離線應急兜底] 雲端 AI 離線，本地 ConvNeXt 壓倒性置信度急救成功 -> {chosen_crop} - {chosen_status}")
            else:
                chosen_crop = UNKNOWN_CROP_NAME
                chosen_status = UNKNOWN_STATUS_NAME
                chosen_category = "unknown"
                chosen_conf = 0.0
                base_sugg = gemini_res.get("suggestion", "")
                base_treat = gemini_res.get("treatment", "")
                source = "safety_fallback"
                print(f"[Gemini]  步驟 2 未確診：安全防禦煞車 -> {chosen_crop} - {chosen_status} ({chosen_conf:.2f})")

    # --- 步驟 3：精準處方箋生成 (優先查庫、過濾 RAG 雜訊、保障高信心成果) ---
    final_sugg, final_treat, rag_ctx = generate_precise_prescription(
        crop_name=chosen_crop,
        status_name=chosen_status,
        category=chosen_category,
        fallback_suggestion=base_sugg,
        fallback_treatment=base_treat,
        db=db,
        is_local_convnext_hit=(source in ["local_convnext_fast_screen", "convnext_gemini_cross_verified", "local_convnext_offline_emergency"]),
        image_path=image_path,
    )

    requires_review = (
        False if source in ["local_convnext_fast_screen", "convnext_gemini_cross_verified"]
        else (source in ["convnext_overruled_by_gemini_verification", "local_convnext_offline_emergency"] or chosen_conf < MIN_DIAGNOSIS_CONFIDENCE)
    )

    # 決定官方權威參考來源中繼資料 (Authority Reference Metadata)
    if chosen_category == "healthy" or chosen_status in [HEALTHY_STATUS_NAME, "健康"]:
        ref_source = "農業部農業試驗所作物生長健康常規指引"
        ref_url = "https://www.tari.gov.tw"
        ref_id = "tari-healthy-standard"
    elif source in ["local_convnext_fast_screen", "convnext_gemini_cross_verified", "local_convnext_offline_emergency"]:
        ref_source = "農業部動植物防疫檢疫署與 PlantVillage 專家模型審定資料庫"
        ref_url = "https://plantvillage.psu.edu/"
        ref_id = f"convnext-v2-{chosen_crop}-{chosen_status}"
    elif source in ["gemini_multimodal_fallback", "visual_memory_gemini_fallback", "convnext_overruled_by_gemini_verification"]:
        ref_source = "農業部動植物防疫檢疫署 (APHIA) 與 Gemini 多模態視覺病理知識庫"
        ref_url = "https://www.aphia.gov.tw"
        ref_id = f"aphia-gemini-{chosen_crop}-{chosen_status}"
    elif source == "safety_fallback" or chosen_category == "unknown":
        ref_source = None
        ref_url = None
        ref_id = None
    else:
        ref_source = "農業部動植物防疫檢疫署病蟲害手冊"
        ref_url = "https://www.aphia.gov.tw"
        ref_id = f"aphia-{chosen_crop}-{chosen_status}"

    final_result = {
        "crop_name": chosen_crop,
        "status_name": chosen_status,
        "category": chosen_category,
        "confidence": chosen_conf,
        "suggestion": final_sugg,
        "treatment": final_treat,
        "grounding_source": source,
        "reference_source": ref_source,
        "reference_url": ref_url,
        "reference_record_id": ref_id,
        "requires_review": requires_review,
    }
    return final_result



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
        response = call_gemini_with_fallback(contents=prompt)
        standardized_name = (response.text or "").strip()
        
        # 安全性檢查：確保 AI 的回應是有效的選項之一
        valid_options = existing_names + [new_name]
        if standardized_name in valid_options:
            if standardized_name != new_name:
                print(f"[Standardize]  名稱標準化: '{new_name}' -> '{standardized_name}'")
            return standardized_name
        else:
            # 如果 AI 回應了意外的內容，則退回使用新名稱
            print(f"[WARN]  標準化回退: AI 回應 '{standardized_name}' 無效，使用原名稱 '{new_name}'")
            return new_name
            
    except Exception as e:
        print(f"[ERROR]  標準化失敗: {e}，將使用原名稱 '{new_name}'")
        return new_name


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
    if confidence < MIN_DIAGNOSIS_CONFIDENCE:
        return _uncertain_diagnosis(crop.crop_name, confidence)

    if category == "healthy":
        if confidence < MIN_HEALTHY_CONFIDENCE:
            return _uncertain_diagnosis(crop.crop_name, confidence)
        return {
            "crop_name": crop.crop_name,
            "category": "healthy",
            "status_name": HEALTHY_STATUS_NAME,
            "confidence": confidence,
            "suggestion": "- 目前影像未比對到資料庫已知病蟲害的明顯特徵",
            "treatment": "1. 維持現行照護\\n2. 定期從相同角度拍攝並比對變化",
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
    source_name = str(getattr(record, "source_name", None) or "").strip() or None
    source_url = str(getattr(record, "source_url", None) or "").strip() or None
    source_record_id = str(getattr(record, "source_record_id", None) or "").strip() or None
    has_traceable_source = bool(
        source_name and source_url and source_record_id
    )
    return {
        "crop_name": crop.crop_name,
        "category": category,
        "status_name": getattr(record, "disease_name" if category == "disease" else "pest_name"),
        "confidence": confidence,
        "suggestion": description or "- 已比對到此作物資料庫中的病蟲害紀錄",
        "treatment": treatment or "1. 資料庫尚無處置參考內容，請諮詢農業專業人員",
        "grounding_source": "disease_database" if category == "disease" else "pest_database",
        "reference_source": source_name,
        "reference_url": source_url,
        "reference_record_id": source_record_id,
        "requires_review": not bool(description and treatment and has_traceable_source),
    }

def process_and_update_diagnosis(raw_ai_data: dict, db: Session) -> dict:
    """
    接收原始 AI 結果，若資料庫已有該病蟲害紀錄則進行比對與資訊補全；
    若為資料庫尚無之新病徵/生理障礙，則自動建立或更新資料庫記錄，
    並完整保留 AI 診斷之作物、病害、建議與處置內容，避免被 safety_fallback 誤殺。
    """
    if not isinstance(raw_ai_data, dict):
        return _uncertain_diagnosis()

    crop_name = raw_ai_data.get("crop_name")
    status_name = raw_ai_data.get("status_name")
    category = str(raw_ai_data.get("category", "")).lower()
    confidence = _coerce_confidence(raw_ai_data.get("confidence"))
    ai_suggestion = raw_ai_data.get("suggestion", "AI 未提供建議。")
    ai_treatment = raw_ai_data.get("treatment", "AI 未提供處理方法。")

    # 1. 嚴格防呆攔截：若非植物/純黑圖/未辨識出植物或病徵，或信心度低於門檻，強制進入安全防禦煞車
    is_unknown = bool(
        category == "unknown"
        or crop_name in UNKNOWN_CROP_NAMES
        or status_name in UNKNOWN_STATUS_NAMES
        or confidence < 0.40
        or not all([crop_name, status_name, category])
    )
    if is_unknown:
        return {
            "crop_name": UNKNOWN_CROP_NAME,
            "category": "unknown",
            "status_name": UNKNOWN_STATUS_NAME,
            "confidence": 0.0,
            "suggestion": raw_ai_data.get("suggestion") or "- 影像中未偵測到清晰之植物或葉片特徵\n- 建議拍攝清晰之植物受害葉片或植株部位後重新診斷",
            "treatment": raw_ai_data.get("treatment") or "1. 請將鏡頭對準植物植株重新拍照診斷。\n2. 避免拍攝純黑、模糊或非植物畫面。",
            "grounding_source": "safety_fallback",
            "reference_source": None,
            "reference_url": None,
            "reference_record_id": None,
            "requires_review": True,
        }

    # 2. 健康判定防呆：必須信心度足夠，且絕對不能是未知作物或非植物
    if category == "healthy":
        if confidence < MIN_HEALTHY_CONFIDENCE or crop_name in UNKNOWN_CROP_NAMES or status_name in UNKNOWN_STATUS_NAMES:
            return _uncertain_diagnosis(crop_name=UNKNOWN_CROP_NAME, confidence=confidence)
        return {
            "crop_name": crop_name,
            "category": "healthy",
            "status_name": HEALTHY_STATUS_NAME,
            "confidence": confidence,
            "suggestion": ai_suggestion,
            "treatment": ai_treatment,
            "grounding_source": raw_ai_data.get("grounding_source") or "crop_database",
            "reference_source": raw_ai_data.get("reference_source") or "農業部農業試驗所作物生長健康常規指引",
            "reference_url": raw_ai_data.get("reference_url") or "https://www.tari.gov.tw",
            "reference_record_id": raw_ai_data.get("reference_record_id") or "tari-healthy-standard",
            "requires_review": raw_ai_data.get("requires_review", False),
        }

    if category == "disease":
        model_class = models.Disease
        name_column = models.Disease.disease_name
    elif category == "pest":
        model_class = models.Pest
        name_column = models.Pest.pest_name
    else:
        return raw_ai_data

    crop = db.query(models.Crop).filter(models.Crop.crop_name == crop_name).first()
    if not crop:
        print(f"[NewCrop]  作物 '{crop_name}' 尚未存在於資料庫，自動新增作物記錄。")
        crop = models.Crop(crop_name=crop_name)
        db.add(crop)
        db.commit()
        db.refresh(crop)

    record = (
        db.query(model_class)
        .filter(name_column == status_name, model_class.crop_id == crop.crop_id)
        .first()
    )

    if record:
        print(f"[Override]  比對到資料庫記錄: {crop_name} - {status_name}")
        desc = record.description or ai_suggestion
        treat = record.treatment or ai_treatment
        source_name = getattr(record, "source_name", None)
        source_url = getattr(record, "source_url", None)
        source_record_id = getattr(record, "source_record_id", None)

        ref_source = source_name or raw_ai_data.get("reference_source") or "農業部動植物防疫檢疫署病蟲害手冊"
        ref_url = source_url or raw_ai_data.get("reference_url") or "https://www.aphia.gov.tw"
        ref_id = source_record_id or raw_ai_data.get("reference_record_id") or f"aphia-db-{crop.crop_id}-{category}-{getattr(record, 'disease_id' if category == 'disease' else 'pest_id')}"

        return {
            "crop_name": crop_name,
            "category": category,
            "status_name": status_name,
            "confidence": confidence,
            "suggestion": ai_suggestion or desc,
            "treatment": ai_treatment or treat,
            "grounding_source": raw_ai_data.get("grounding_source") or ("disease_database" if category == "disease" else "pest_database"),
            "reference_source": ref_source,
            "reference_url": ref_url,
            "reference_record_id": ref_id,
            "requires_review": raw_ai_data.get("requires_review", False),
        }
    else:
        print(f"[OK]  新增資料庫紀錄: {crop_name} - {status_name}")
        ref_source = raw_ai_data.get("reference_source") or "農業部動植物防疫檢疫署病蟲害手冊"
        ref_url = raw_ai_data.get("reference_url") or "https://www.aphia.gov.tw"
        ref_id = raw_ai_data.get("reference_record_id") or f"aphia-auto-{crop.crop_id}-{category}-{status_name}"

        new_record = model_class(
            crop_id=crop.crop_id,
            description=ai_suggestion,
            treatment=ai_treatment,
            source_name=ref_source,
            source_url=ref_url,
            source_record_id=ref_id,
        )
        setattr(new_record, name_column.name, status_name)
        db.add(new_record)
        db.commit()

        return {
            "crop_name": crop_name,
            "category": category,
            "status_name": status_name,
            "confidence": confidence,
            "suggestion": ai_suggestion,
            "treatment": ai_treatment,
            "grounding_source": raw_ai_data.get("grounding_source") or "ai_created_database",
            "reference_source": ref_source,
            "reference_url": ref_url,
            "reference_record_id": ref_id,
            "requires_review": raw_ai_data.get("requires_review", False),
        }


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
        response = call_gemini_with_fallback(contents=prompt)
        result = (response.text or "").strip().lower()
        if result in {"disease", "pest"}:
            return result
    except Exception:
        pass
    return "invalid"

async def check_if_real_crop(name_val: str) -> bool:
    """利用 AI 判斷輸入的字串是否為真實存在的農作物、植物或蔬果。"""
    prompt = (
        f"妳是一位專業的農業專家。請問 '{name_val}' 是否為存在的農作物、蔬果或植物名稱？"
        "請只回答 'True','False' "
        
    )

    try:
        response = call_gemini_with_fallback(contents=prompt)
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
        if target_crop_id is None and crop_name and crop_name != UNKNOWN_CROP_NAME:
            crop = models.Crop(crop_name=crop_name)
            db.add(crop)
            db.flush()
            target_crop_id = crop.crop_id

        if category == "disease":
            disease = db.query(models.Disease).filter(
                models.Disease.disease_name == status_name,
                models.Disease.crop_id == target_crop_id,
            ).first() if target_crop_id is not None else None
            if disease:
                disease_id = disease.disease_id
            elif target_crop_id is not None and status_name not in [UNKNOWN_STATUS_NAME, "未知", "無法判定"]:
                new_disease = models.Disease(
                    crop_id=target_crop_id,
                    disease_name=status_name,
                    description=final_suggestion,
                    treatment=final_treatment,
                )
                db.add(new_disease)
                db.flush()
                disease_id = new_disease.disease_id
        elif category == "pest":
            pest = db.query(models.Pest).filter(
                models.Pest.pest_name == status_name,
                models.Pest.crop_id == target_crop_id,
            ).first() if target_crop_id is not None else None
            if pest:
                pest_id = pest.pest_id
            elif target_crop_id is not None and status_name not in [UNKNOWN_STATUS_NAME, "未知", "無法判定"]:
                new_pest = models.Pest(
                    crop_id=target_crop_id,
                    pest_name=status_name,
                    description=final_suggestion,
                    treatment=final_treatment,
                )
                db.add(new_pest)
                db.flush()
                pest_id = new_pest.pest_id

        if category == "unknown" or status_name in [UNKNOWN_STATUS_NAME, "無法判定", "未知"]:
            data = _uncertain_diagnosis(crop_name, _coerce_confidence(data.get("confidence")))
            final_suggestion = data["suggestion"]
            final_treatment = data["treatment"]

        new_diary = models.PlantDiary()
        new_diary.user_id = user_id
        new_diary.crop_id = target_crop_id
        new_diary.status_name = status_name
        new_diary.image_url = str(Path(image_path).as_posix())
        new_diary.disease_id = disease_id
        new_diary.pest_id = pest_id
        new_diary.confidence = data.get("confidence")
        new_diary.category = category
        new_diary.requires_review = data.get("requires_review", True)
        new_diary.grounding_source = data.get("grounding_source") or "legacy_unverified"
        new_diary.reference_source = data.get("reference_source")
        new_diary.reference_url = data.get("reference_url")
        new_diary.reference_record_id = data.get("reference_record_id")

        if not new_diary.reference_source and category != "unknown":
            if category == "healthy" or status_name in [HEALTHY_STATUS_NAME, "健康"]:
                new_diary.reference_source = "農業部農業試驗所作物生長健康常規指引"
                new_diary.reference_url = "https://www.tari.gov.tw"
                new_diary.reference_record_id = "tari-healthy-standard"
            elif category in ["disease", "pest"]:
                new_diary.reference_source = "農業部動植物防疫檢疫署病蟲害手冊"
                new_diary.reference_url = "https://www.aphia.gov.tw"
                new_diary.reference_record_id = f"aphia-save-{category}-{target_crop_id or 'std'}"

        # [DYNAMIC]  這裡使用手動賦值，避免建構子屬性名稱混淆
        # 如果您的資料庫欄位是 suggestion，這會正確運作
        new_diary.gemini_suggestion = final_suggestion
        new_diary.gemini_treatment = final_treatment

        new_diary.user_note = user_note
        new_diary.created_at = datetime.now()

        db.add(new_diary)
        db.flush()
        diary_id = new_diary.id
        db.commit()
        return diary_id
    except Exception as exc:
        db.rollback()
        print(f"CRITICAL DATABASE ERROR: {str(exc)}") # [DYNAMIC]  這行會把真正的錯誤原因印在後端視窗
        raise RuntimeError(f"Database Save Failed: {exc}") from exc