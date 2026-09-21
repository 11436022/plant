import pytest
from app.services.ai import (
    arbitrate_diagnosis,
    parse_custom_label,
    UNKNOWN_CROP_NAME,
    UNKNOWN_STATUS_NAME,
    HEALTHY_STATUS_NAME,
)


def test_parse_custom_label():
    assert parse_custom_label("扶桑-缺鐵症") == ("扶桑", "缺鐵症")
    assert parse_custom_label("扁蒲-健康") == ("扁蒲", "健康")
    assert parse_custom_label("樟木-葉斑病") == ("樟木", "葉斑病")
    assert parse_custom_label("") == (UNKNOWN_CROP_NAME, UNKNOWN_STATUS_NAME)
    assert parse_custom_label("無連字號標籤") == ("無連字號標籤", UNKNOWN_STATUS_NAME)


def test_scenario_1_double_hit_agreement():
    """情境 1：雙重命中 (Gemini 與客製化模型皆認出扁蒲健康)"""
    gemini_result = {
        "crop_name": "扁蒲",
        "status_name": "健康",
        "category": "healthy",
        "confidence": 0.90,
        "suggestion": "- 葉片翠綠飽滿\n- 無可見病蟲害",
        "treatment": "持續維持適當灌溉與日照。",
    }
    custom_result = {
        "label": "扁蒲-健康",
        "score": 0.96,
        "crop_name": "扁蒲",
        "status_name": "健康",
    }

    verdict = arbitrate_diagnosis(gemini_result, custom_result)

    assert verdict["crop_name"] == "扁蒲"
    assert verdict["status_name"] == "健康"
    assert verdict["category"] == "healthy"
    assert verdict["confidence"] == 0.96
    assert verdict["grounding_source"] == "tripartite_verified_custom_hit"
    assert verdict["requires_review"] is False


def test_scenario_2_ood_custom_discarded_strawberry():
    """情境 2：分佈外作物 (草莓)，客製化模型不在白名單內，強制捨棄客製化模型猜測"""
    gemini_result = {
        "crop_name": "草莓",
        "status_name": "灰黴病",
        "category": "disease",
        "confidence": 0.92,
        "suggestion": "- 葉片與果實周圍有灰色黴菌\n- 局部組織軟化壞死",
        "treatment": "1. 剪除發黴葉片與病果。\n2. 加強通風並降低濕度。",
    }
    # 即使客製化模型因為只有3個按鈕而硬猜並碰巧給出高分，依然必須被直接捨棄
    custom_result = {
        "label": "樟木-葉斑病",
        "score": 0.85,
        "crop_name": "樟木",
        "status_name": "葉斑病",
    }

    verdict = arbitrate_diagnosis(gemini_result, custom_result)

    assert verdict["crop_name"] == "草莓"
    assert verdict["status_name"] == "灰黴病"
    assert verdict["category"] == "disease"
    assert verdict["confidence"] == 0.92
    assert verdict["grounding_source"] == "gemini_rag_ood_custom_discarded"
    assert verdict["requires_review"] is False


def test_scenario_3_reverse_rescue_unknown_crop():
    """情境 3：特寫導致 Gemini 無法辨識植物 (未知作物)，但客製化模型高信心反向救援成功"""
    gemini_result = {
        "crop_name": "未知作物",
        "status_name": "無法判定",
        "category": "unknown",
        "confidence": 0.35,
        "suggestion": "- 葉肉褪綠變黃，但葉脈依然保持鮮綠色",
        "treatment": "特徵不足，請補拍全株照片。",
    }
    custom_result = {
        "label": "扶桑-缺鐵症",
        "score": 0.93,
        "crop_name": "扶桑",
        "status_name": "缺鐵症",
    }

    verdict = arbitrate_diagnosis(gemini_result, custom_result)

    assert verdict["crop_name"] == "扶桑"
    assert verdict["status_name"] == "缺鐵症"
    assert verdict["confidence"] == 0.93
    assert verdict["grounding_source"] == "custom_model_reverse_rescue"
    assert verdict["requires_review"] is False
    assert "反向救援" in verdict["suggestion"]


def test_scenario_4_disease_conflict_hibiscus_albinism():
    """情境 4：同作物但病害衝突 (扶桑白化症 vs 扶桑缺鐵症)，採納 Gemini 並標記專家審核"""
    gemini_result = {
        "crop_name": "扶桑",
        "status_name": "白化症",
        "category": "disease",
        "confidence": 0.88,
        "suggestion": "- 全葉呈現均勻乳白色\n- 葉脈亦無綠色殘留，不符合一般缺鐵綠脈特徵",
        "treatment": "可能為遺傳突變或嚴重白化症，建議先移至散射光處觀察。",
    }
    custom_result = {
        "label": "扶桑-缺鐵症",
        "score": 0.82,
        "crop_name": "扶桑",
        "status_name": "缺鐵症",
    }

    verdict = arbitrate_diagnosis(gemini_result, custom_result)

    assert verdict["crop_name"] == "扶桑"
    assert verdict["status_name"] == "白化症"
    assert verdict["confidence"] == 0.88
    assert verdict["grounding_source"] == "tripartite_conflict_flagged_for_review"
    assert verdict["requires_review"] is True
    assert "⚠️ 診斷分歧提醒" in verdict["suggestion"]


def test_scenario_5_safety_fallback_both_uncertain():
    """情境 5：兩者皆不確定時，安全防禦煞車，引導重拍"""
    gemini_result = {
        "crop_name": "未知作物",
        "status_name": "無法判定",
        "category": "unknown",
        "confidence": 0.20,
        "suggestion": "- 模糊無法辨識",
        "treatment": "請重拍。",
    }
    custom_result = {
        "label": "樟木-葉斑病",
        "score": 0.25,
        "crop_name": "樟木",
        "status_name": "葉斑病",
    }

    verdict = arbitrate_diagnosis(gemini_result, custom_result)

    assert verdict["crop_name"] == UNKNOWN_CROP_NAME
    assert verdict["status_name"] == UNKNOWN_STATUS_NAME
    assert verdict["grounding_source"] == "safety_fallback"
    assert verdict["requires_review"] is True

