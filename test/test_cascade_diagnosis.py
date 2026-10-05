from unittest.mock import patch
import pytest
from app.services.ai import diagnostic_plant, generate_precise_prescription
from app.services.convnext import (
    parse_convnext_prediction,
    match_crop_to_class,
    get_convnext_model,
    load_class_index,
    predict_convnext_fast_screen,
)


def test_convnext_label_mapping():
    crop, status, category = parse_convnext_prediction("Tomato___Early_blight")
    assert crop == "番茄"
    assert status == "早疫病"
    assert category == "disease"

    crop, status, category = parse_convnext_prediction("Apple___healthy")
    assert crop == "蘋果"
    assert status == "健康"
    assert category == "healthy"


def test_match_crop_to_class():
    assert match_crop_to_class("番茄", "Tomato___Early_blight") is True
    assert match_crop_to_class("Tomato", "Tomato___Late_blight") is True
    assert match_crop_to_class("蘋果", "Tomato___Early_blight") is False
    assert match_crop_to_class("甜椒", "Pepper,_bell___healthy") is True


def test_convnext_real_weights_loadable():
    """驗證使用者加入的 convnext_plant_best.pth 與 idx_to_class.json 可正常載入。"""
    classes = load_class_index()
    assert len(classes) == 38
    model = get_convnext_model()
    assert model is not None


def test_tier_1_convnext_fast_screen_hit():
    """步驟 1：本地 ConvNeXt 快篩命中 (限定番茄且信心 >= 75%)。"""
    mock_convnext = {
        "crop_name": "番茄",
        "status_name": "早疫病",
        "category": "disease",
        "confidence": 0.89,
        "grounding_source": "local_convnext_fast_screen",
        "requires_review": False,
    }

    result = diagnostic_plant(
        image_path="dummy.jpg",
        crop_hint="番茄",
        mock_convnext_result=mock_convnext,
    )

    assert result["crop_name"] == "番茄"
    assert result["status_name"] == "早疫病"
    assert result["category"] == "disease"
    assert result["confidence"] == 0.89
    assert result["grounding_source"] == "local_convnext_fast_screen"
    assert result["requires_review"] is False
    assert "早疫病" in result["treatment"] or "早疫病" in result["suggestion"] or len(result["treatment"]) > 0


def test_tier_1_convnext_low_confidence_falls_to_gemini():
    """步驟 1 未命中或信心不足，自動流向步驟 2 Gemini 多模態兜底。"""
    mock_gemini = {
        "crop_name": "芒果",
        "status_name": "炭疽病",
        "category": "disease",
        "confidence": 0.88,
        "suggestion": "- 葉片出現黑褐色圓形病斑\n- 嫩葉扭曲壞死",
        "treatment": "1. 剪除發病枝葉並銷毀。\n2. 於發育初期噴灑保護性藥劑。",
    }

    result = diagnostic_plant(
        image_path="dummy.jpg",
        crop_hint="芒果",
        mock_convnext_result=None,
        mock_gemini_result=mock_gemini,
    )

    assert result["crop_name"] == "芒果"
    assert result["status_name"] == "炭疽病"
    assert result["grounding_source"] == "gemini_multimodal_fallback"
    assert result["confidence"] == 0.88


def test_tier_3_rag_healthy_prescription():
    """步驟 3：確診為健康狀態時，輸出標準健康照護處方。"""
    sugg, treat, ctx = generate_precise_prescription(crop_name="番茄", status_name="健康")
    assert "生長強健" in sugg
    assert "澆水" in treat
    assert ctx == "healthy_status"


def test_tier_3_rag_forced_query_fallback():
    """步驟 3：若 RAG 知識庫未匹配特定篇章，平滑降級為結構化處方。"""
    sugg, treat, ctx = generate_precise_prescription(
        crop_name="番茄",
        status_name="晚疫病",
        category="disease",
        fallback_suggestion="- 葉緣出現水浸狀暗綠色病斑",
        fallback_treatment="1. 拔除重病株。\n2. 施用保護性殺菌劑。",
    )
    assert len(sugg) > 0
    assert len(treat) > 0


def test_get_crops_api():
    """測試 GET /api/v1/knowledge/crops 能正常回傳作物清單供前端選單使用。"""
    from starlette.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    response = client.get("/api/v1/knowledge/crops")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "data" in data
    assert isinstance(data["data"], list)


def test_prescription_preserves_high_confidence_fallback():
    """測試未命中知識庫時，能 100% 完整保留並回傳前級高信心的診斷處方，不被 RAG 雜訊覆蓋。"""
    custom_sugg = "- 葉片初期出現水浸狀小斑點\n- 濕度高時迅速擴大"
    custom_treat = "1. 清除病葉。\n2. 改善通風。"
    sugg, treat, ctx = generate_precise_prescription(
        crop_name="神秘作物XYZ",
        status_name="罕見病毒病",
        category="disease",
        fallback_suggestion=custom_sugg,
        fallback_treatment=custom_treat,
    )
    assert sugg == custom_sugg
    assert treat == custom_treat
    assert "未有" not in sugg
    assert "未有" not in treat
    assert ctx == "gemini_multimodal_dynamic_prescription"


def test_database_authoritative_hit_for_repaired_birch():
    """測試已修復的樺木葉斑病能直接命中資料庫權威記錄，不再回傳無效描述。"""
    sugg, treat, ctx = generate_precise_prescription(
        crop_name="樺木",
        status_name="葉斑病",
        category="disease",
    )
    assert "未有樺木" not in sugg
    assert "未有樺木" not in treat
    assert "斑點" in sugg
    assert "清理" in treat or "剪除" in treat
    assert ctx == "mysql_fallback_database"


def test_convnext_overwhelming_override_reversal():
    """測試壓倒性信心反轉機制：使用者選草莓，但模型對番茄具備 95% 壓倒性信心，自動反轉校正。"""
    import torch
    from PIL import Image

    dummy_image = Image.new("RGB", (224, 224), color="green")
    
    # 建立 38 個類別的假機率張量
    fake_probs = torch.zeros(38)
    # 找到 Tomato___Early_blight 的 index 與 Strawberry 類別 index
    idx_map = load_class_index()
    tomato_idx = [i for i, label in idx_map.items() if label == "Tomato___Early_blight"][0]
    strawberry_idx = [i for i, label in idx_map.items() if "Strawberry" in label][0]

    fake_probs[tomato_idx] = 0.95
    fake_probs[strawberry_idx] = 0.02

    with patch("app.services.convnext.Image.open", return_value=dummy_image):
        with patch("app.services.convnext.torch.softmax", return_value=fake_probs.unsqueeze(0)):
            # 使用者指定「草莓」
            result = predict_convnext_fast_screen("dummy.jpg", crop_name="草莓")
            assert result is not None
            assert result["crop_name"] == "番茄"
            assert result["status_name"] == "早疫病"
            assert result["confidence"] == pytest.approx(0.95, abs=0.01)
            assert result["is_confidence_override"] is True


def test_convnext_no_override_when_global_score_not_overwhelming():
    """測試非壓倒性時不反轉：使用者選草莓，全局最高僅 50% (如罕見植物/檸檬)，安全放棄交給 Gemini。"""
    import torch
    from PIL import Image

    dummy_image = Image.new("RGB", (224, 224), color="green")
    fake_probs = torch.zeros(38)
    idx_map = load_class_index()
    tomato_idx = [i for i, label in idx_map.items() if label == "Tomato___Early_blight"][0]
    fake_probs[tomato_idx] = 0.50 # 僅 50%，未達 85% 壓倒性門檻

    with patch("app.services.convnext.Image.open", return_value=dummy_image):
        with patch("app.services.convnext.torch.softmax", return_value=fake_probs.unsqueeze(0)):
            result = predict_convnext_fast_screen("dummy.jpg", crop_name="草莓")
            assert result is None # 安全交棒給 Gemini


def test_convnext_user_crop_respected_when_confident():
    """測試使用者指定作物信心達標時，正常命中不反轉。"""
    import torch
    from PIL import Image

    dummy_image = Image.new("RGB", (224, 224), color="green")
    fake_probs = torch.zeros(38)
    idx_map = load_class_index()
    strawberry_scorch_idx = [i for i, label in idx_map.items() if label == "Strawberry___Leaf_scorch"][0]
    fake_probs[strawberry_scorch_idx] = 0.82 # 草莓達標 82%

    with patch("app.services.convnext.Image.open", return_value=dummy_image):
        with patch("app.services.convnext.torch.softmax", return_value=fake_probs.unsqueeze(0)):
            result = predict_convnext_fast_screen("dummy.jpg", crop_name="草莓")
            assert result is not None
            assert result["crop_name"] == "草莓"
            assert result["status_name"] == "葉焦病"
            assert result["is_confidence_override"] is False


def test_unknown_diagnosis_cannot_be_saved_to_diary():
    """方案 A：驗證當診斷結果為未知植物或無法判定時，confirm_and_create_diary 會被嚴格阻擋 (400)"""
    import asyncio
    from fastapi import HTTPException
    from app.routers.diaries import confirm_and_create_diary
    from app.routers.prediction import prediction_cache
    from app.schemas.diaries import DiaryConfirm
    from unittest.mock import MagicMock

    pred_id = "test-unknown-id-123"
    prediction_cache[pred_id] = {
        "result": {
            "crop_name": "未知作物",
            "status_name": "無法判定",
            "category": "unknown",
            "confidence": 0.2,
        },
        "temp_path": "static/tmp/dummy.jpg"
    }

    mock_user = MagicMock()
    mock_user.user_id = 1
    mock_db = MagicMock()
    payload = DiaryConfirm(user_note="想存未知", disease_name="無法判定", gemini_advice="特徵不足")

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            confirm_and_create_diary(
                prediction_id=pred_id,
                payload=payload,
                current_user=mock_user,
                db=mock_db
            )
        )

    assert exc_info.value.status_code == 400
    assert "不可存入病歷日記" in exc_info.value.detail


def test_convnext_delegates_banana_to_gemini():
    """驗證當使用者上傳香蕉（非 PlantVillage 閉集作物）時，ConvNeXt 快篩安全放棄，交由 Gemini 診斷。"""
    result = predict_convnext_fast_screen("dummy.jpg", crop_name="香蕉")
    assert result is None


def test_convnext_delegates_unknown_crop_to_gemini():
    """驗證當使用者未指定作物（未知）時，ConvNeXt 快篩不隨意瞎猜閉集桃子/番茄，安全交由 Gemini 進行開集辨識。"""
    result_none = predict_convnext_fast_screen("dummy.jpg", crop_name=None)
    assert result_none is None

    result_unknown = predict_convnext_fast_screen("dummy.jpg", crop_name="未知")
    assert result_unknown is None


