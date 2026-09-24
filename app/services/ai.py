import base64
import json
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

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

UNKNOWN_CROP_NAME = "未知作物"
UNKNOWN_STATUS_NAME = "無法判定"
HEALTHY_STATUS_NAME = "健康"
MIN_DIAGNOSIS_CONFIDENCE = 0.65
MIN_HEALTHY_CONFIDENCE = 0.85


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


def arbitrate_diagnosis(
    gemini_result: dict | None,
    custom_result: dict | None,
    retrieved_rag_context: str = "",
) -> dict:
    """
    後端大法官：三方會診（Vertex AI 客製化模型、Gemini 多模態、RAG 知識庫）裁決核心。
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
                    f"⚠️ 診斷分歧提醒：通用AI診斷為【{gemini_raw_status}】，專屬模型預測為【{custom_status}】"
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
                f"🌟 專屬模型反向救援：依病徵特寫高信心 ({custom_score:.2f}) 辨識為【{custom_crop} - {custom_status}】\n"
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
    if status_name in [HEALTHY_STATUS_NAME, "健康"]:
        suggestion = "- 植株生長強健，葉色均勻鮮綠，無枯黃萎凋或異常捲曲變形\n- 葉面及葉背均無明顯病斑、白粉、黴菌或害蟲侵蝕痕跡"
        treatment = "1. 維持當前適度日照與澆水頻率，避免盆土長期積水爛根。\n2. 保持良好通風環境，適時修剪老葉促進通風與生長。\n3. 定期檢查葉背與莖部新芽，持續做好日常田間衛生與預防。"
        return suggestion, treatment, "healthy_status"

    if status_name in [UNKNOWN_STATUS_NAME, "無法判定"]:
        sugg = fallback_suggestion or "- 影像特徵不足，無法與目前資料庫中的作物或病害特徵安全對應\n- 建議重新拍攝清晰葉面、莖部與受害區域"
        treat = fallback_treatment or "1. 暫時隔離疑似受害植株並持續觀察。\n2. 補拍清晰照片後重新診斷。\n3. 若症狀持續擴大，請諮詢農業專家或更新知識庫。"
        return sugg, treat, ""

    def _is_invalid_text(t: str) -> bool:
        """偵測是否為交白卷或官腔廢話。"""
        if not t or len(t.strip()) < 15:
            return True
        markers = ["未有", "未記載", "知識庫未", "未提供具體", "未有具體", "無法提供"]
        return any(m in t for m in markers)

    # --- 來源 1：本地 ConvNeXt 命中！100% 本地產出階梯式輕重處方 (零調用 Gemini，零 API 費用) ---
    if is_local_convnext_hit:
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
            except Exception:
                pass
            finally:
                if should_close_db and local_db:
                    local_db.close()

        feature_text = base_desc if base_desc else f"植株葉片出現【{status_name}】之典型病徵斑點與組織變色。"
        treatment_text = base_treat_db if base_treat_db else f"參照【{crop_name} - {status_name}】植物保護手冊，於發病初期施用登記推薦藥劑或安全防治資材。"

        convnext_sugg = (
            f"- 【病徵特徵】：{feature_text}\n"
            f"- 【輕度初期】：若僅零星 1-2 片葉片或葉緣出現小斑點，其餘植株鮮綠健壯。\n"
            f"- 【重度擴散】：若多數葉片出現大面積輪紋、壞疽枯萎或蔓延至莖桿。"
        )
        convnext_treat = (
            f"1. 【初期輕微處置】：及早剪除少量發病葉片並妥善丟棄；維持充足日照並改善通風，澆水時避免噴濕葉面，無須施藥即可自然控制。\n"
            f"2. 【中重度擴散處置】：徹底清除嚴重病葉並清理地面落葉；{treatment_text}\n"
            f"3. 【環境防護管理】：適當拉開植株間距降低濕度，發病期暫停施用高氮肥料，保持盆土透氣瀝水避免病菌滋生。"
        )
        print(f"🚀 本地 ConvNeXt 命中：100% 本地生成階梯式輕重處方 (0 雲端 API 費用，零延遲)")
        return convnext_sugg, convnext_treat, "convnext_local_graded_prescription"

    # --- 來源 2：Gemini 多模態看圖兜底成果 (當 ConvNeXt 未命中時，採用 Gemini 針對該照片輕重視角所產生的處方) ---
    if fallback_suggestion and fallback_treatment and not _is_invalid_text(fallback_suggestion) and not _is_invalid_text(fallback_treatment):
        print(f"🌟 採用 Gemini 看圖動態處置：依當前照片病徵輕重度專屬生成 (長度: {len(fallback_suggestion)}/{len(fallback_treatment)})")
        return fallback_suggestion, fallback_treatment, "gemini_multimodal_dynamic_prescription"

    # --- 備用來源 3：查詢 MySQL 本地專家資料庫記錄 (作為離線或 AI 異常時的保險備援) ---
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
                    record = local_db.query(models.Pest).filter(
                        models.Pest.crop_id == crop_record.crop_id,
                        models.Pest.pest_name.like(f"%{status_name}%")
                    ).first()
                else:
                    record = local_db.query(models.Disease).filter(
                        models.Disease.crop_id == crop_record.crop_id,
                        models.Disease.disease_name.like(f"%{status_name}%")
                    ).first()

                if record and record.description and record.treatment:
                    if not _is_invalid_text(record.description) and not _is_invalid_text(record.treatment):
                        print(f"📖 離線備援啟用：採用專家資料庫標準指引 -> {crop_name} - {status_name}")
                        return record.description, record.treatment, "mysql_fallback_database"
        except Exception as db_err:
            print(f"⚠️ 查詢備援資料庫出錯: {db_err}")
        finally:
            if should_close_db and local_db:
                local_db.close()

    # --- 備用來源 4：安全通用專家處方 (最底層保險) ---
    print(f"ℹ️ 使用通用安全農業處方: {crop_name} - {status_name}")
    safe_sugg = (
        f"- 植株出現典型【{status_name}】病徵，葉面可見局部色斑、組織壞死或水浸狀病斑\n"
        f"- 隨病程進展，病斑周圍可能伴隨黃暈，需注意相鄰葉片與枝條是否有擴散跡象\n"
        f"- 潮濕多雨時病部可能滋生細微黴狀物或微細黑色分生子器"
    )
    safe_treat = (
        f"1. 即時修剪並徹底清除罹病葉片與枯枝，裝袋集中銷毀，阻斷初次及再次感染源。\n"
        f"2. 加強田間通風與採光，適度整枝修剪，避免密植導致高溫高濕之微氣候。\n"
        f"3. 澆水時採取滴灌或盆土注水，避免噴灌弄濕葉面；發病期間避免過量施用氮肥。\n"
        f"4. 參照【{crop_name} - {status_name}】植物保護手冊，於發病初期施用登記推薦藥劑或廣效保護型殺菌劑（如波爾多液、三氟敏等）。"
    )
    return safe_sugg, safe_treat, "general_safe_prescription"


def _call_gemini_fallback(
    image_path: str,
    crop_hint: str | None = None,
    mock_result: dict | None = None,
) -> dict:
    """步驟 3：Gemini 多模態兜底推論。"""
    if mock_result is not None:
        return mock_result

    img = Image.open(image_path)
    if crop_hint:
        user_crop_instruction = (
            f"已知使用者指定/選定的作物名稱為：【{crop_hint}】。"
            f"請以該作物為基準，專注鑑別長尾、罕見病徵、生理障礙或害蟲，並回傳精確病害名稱（或判定為 '健康'）。"
            f"若影像特徵嚴重明顯與【{crop_hint}】違背，請依專業視覺判斷修正作物名稱。"
        )
    else:
        user_crop_instruction = "請辨識影像中的植物名稱（crop_name）及其健康狀態（status_name，如特定病害、蟲害，或 '健康'）。"

    prompt = f"""
    You are a top-tier plant pathologist.
    {user_crop_instruction}

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
      "suggestion": "string (2-3 點核心視覺特徵，每點以 '-' 開頭，'\\n' 換行)",
      "treatment": "string (可執行的處置步驟，每點以 '1.', '2.' 等開頭，'\\n' 換行)"
    }}
    """
    try:
        response = client.models.generate_content(model="gemini-2.5-flash", contents=[prompt, img])
        clean_text = (response.text or "").replace("```json", "").replace("```", "").strip()
        return json.loads(clean_text)
    except Exception as e:
        print(f"❌ Gemini 多模態兜底失敗: {e}")
        return _uncertain_diagnosis(crop_name=crop_hint)


def diagnostic_plant(
    image_path: str,
    crop_hint: str | None = None,
    mock_convnext_result: dict | None = None,
    mock_gemini_result: dict | None = None,
    db: Session | None = None,
    **kwargs,
) -> dict:
    """
    三層瀑布流階層式植物診斷架構 (Three-Tier Cascade Diagnosis Engine):
    步驟 1: 本地模型 (ConvNeXt) 優先快篩 (已支援 38 類 PlantVillage 病害，限定選定作物比對，>= 75% 命中)
    步驟 2: Gemini 多模態兜底 (已知植物定向診斷，或未知植物自動識別長尾病徵)
    步驟 3: 精準 RAG 檢索 (強制 Query: [植物名稱] + [確診病名] -> 100% 精準處方箋)
    """
    clean_crop = (
        crop_hint.strip()
        if crop_hint and crop_hint.strip() not in ["未知", "未知作物", "未知植物", "無法判定"]
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
        if convnext_hit.get("is_confidence_override"):
            print(f"🚀 步驟 1 命中：本地 ConvNeXt 壓倒性信心反轉成功 -> {chosen_crop} - {chosen_status} ({chosen_conf:.2f})")
        else:
            print(f"🚀 步驟 1 命中：本地 ConvNeXt 快篩成功 -> {chosen_crop} - {chosen_status} ({chosen_conf:.2f})")

    # --- 步驟 2：Gemini 多模態兜底 (若步驟 1 未命中) ---
    if not chosen_crop:
        gemini_res = _call_gemini_fallback(
            image_path=image_path,
            crop_hint=clean_crop,
            mock_result=mock_gemini_result,
        )
        chosen_crop = gemini_res.get("crop_name") or clean_crop or UNKNOWN_CROP_NAME
        chosen_status = gemini_res.get("status_name") or UNKNOWN_STATUS_NAME
        chosen_category = gemini_res.get("category", "unknown")
        chosen_conf = _coerce_confidence(gemini_res.get("confidence", 0.0))
        base_sugg = gemini_res.get("suggestion", "")
        base_treat = gemini_res.get("treatment", "")
        source = "gemini_multimodal_fallback"
        print(f"🌐 步驟 2 命中：Gemini 多模態兜底完成 -> {chosen_crop} - {chosen_status} ({chosen_conf:.2f})")

    # --- 步驟 3：精準處方箋生成 (優先查庫、過濾 RAG 雜訊、保障高信心成果) ---
    final_sugg, final_treat, rag_ctx = generate_precise_prescription(
        crop_name=chosen_crop,
        status_name=chosen_status,
        category=chosen_category,
        fallback_suggestion=base_sugg,
        fallback_treatment=base_treat,
        db=db,
        is_local_convnext_hit=(source == "local_convnext_fast_screen"),
    )

    final_result = {
        "crop_name": chosen_crop,
        "status_name": chosen_status,
        "category": chosen_category,
        "confidence": chosen_conf,
        "suggestion": final_sugg,
        "treatment": final_treat,
        "grounding_source": source,
        "requires_review": False
        if source == "local_convnext_fast_screen"
        else (chosen_conf < MIN_DIAGNOSIS_CONFIDENCE),
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
            "grounding_source": raw_ai_data.get("grounding_source") or "ai_direct_result",
            "requires_review": raw_ai_data.get("requires_review", False),
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
        # 作物不存在於本地資料庫中，自動為其建立作物記錄，避免覆蓋丟棄 AI 的可信診斷結果
        print(f"🌱 作物 '{crop_name}' 尚未存在於資料庫，自動新增作物記錄。")
        crop = models.Crop(crop_name=crop_name)
        db.add(crop)
        db.commit()
        db.refresh(crop)

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
        "grounding_source": raw_ai_data.get("grounding_source") or ("ai_updated_database" if record else "ai_created_database"),
        "requires_review": raw_ai_data.get("requires_review", False),
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