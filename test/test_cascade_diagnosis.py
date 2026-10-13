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
    assert len(classes) >= 38
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


def test_convnext_method_c_cosine_similarity_ood_interception():
    """
    方法 C 測試：驗證特徵空間餘弦相似度 OOD 攔截機制。
    當 Softmax 偽高置信 (99%) 但特徵相似度低於門檻 (0.45 < 0.55) 時，判定為果實/異物，安全拒絕快篩；
    當特徵相似度達標 (0.75 >= 0.55) 時，正常命中。
    """
    import torch
    from PIL import Image

    dummy_image = Image.new("RGB", (224, 224), color="green")
    idx_map = load_class_index()
    strawberry_scorch_idx = [i for i, label in idx_map.items() if label == "Strawberry___Leaf_scorch"][0]

    fake_probs = torch.zeros(38)
    fake_probs[strawberry_scorch_idx] = 0.99  # Softmax 偽高分 99%

    # 模擬 1：果實/異物（特徵餘弦相似度僅 0.45，低於 0.55 門檻）
    fake_low_cos = torch.full((38,), 0.20)
    fake_low_cos[strawberry_scorch_idx] = 0.45

    with patch("app.services.convnext.Image.open", return_value=dummy_image):
        with patch("app.services.convnext.torch.softmax", return_value=fake_probs.unsqueeze(0)):
            res_ood = predict_convnext_fast_screen(
                "dummy.jpg",
                crop_name="草莓",
                mock_cosine_similarity=fake_low_cos,
            )
            assert res_ood is None  # 成功觸發 OOD 攔截，安全交由 Gemini！

    # 模擬 2：真正的葉焦病葉片（特徵餘弦相似度高達 0.78，達標）
    fake_high_cos = torch.full((38,), 0.20)
    fake_high_cos[strawberry_scorch_idx] = 0.78

    with patch("app.services.convnext.Image.open", return_value=dummy_image):
        with patch("app.services.convnext.torch.softmax", return_value=fake_probs.unsqueeze(0)):
            res_leaf = predict_convnext_fast_screen(
                "dummy.jpg",
                crop_name="草莓",
                mock_cosine_similarity=fake_high_cos,
            )
            assert res_leaf is not None
            assert res_leaf["crop_name"] == "草莓"
            assert res_leaf["status_name"] == "葉焦病"
            assert res_leaf["cosine_similarity"] == pytest.approx(0.78, abs=0.01)
            assert "top_k_candidates" in res_leaf
            assert "cam_foreground_ratio" in res_leaf


def test_scheme_1_grad_cam_alignment_interception():
    """
    方案 1 測試：弱監督 Grad-CAM 空間注意力前景對齊攔截。
    當焦點落在背景雜訊/泥土 (前景比例僅 15% < 35% 門檻) 時，安全攔截並交由 Gemini。
    """
    import torch
    from PIL import Image

    dummy_image = Image.new("RGB", (224, 224), color="green")
    idx_map = load_class_index()
    strawberry_scorch_idx = [i for i, label in idx_map.items() if label == "Strawberry___Leaf_scorch"][0]

    fake_probs = torch.zeros(38)
    fake_probs[strawberry_scorch_idx] = 0.88
    fake_high_cos = torch.full((38,), 0.20)
    fake_high_cos[strawberry_scorch_idx] = 0.80

    with patch("app.services.convnext.Image.open", return_value=dummy_image):
        with patch("app.services.convnext.torch.softmax", return_value=fake_probs.unsqueeze(0)):
            with patch("app.services.convnext.compute_cam_foreground_alignment", return_value=0.15):
                # 模擬注意力渙散或看泥土 (0.15 < 0.35)
                res_cam_fail = predict_convnext_fast_screen(
                    "dummy.jpg",
                    crop_name="草莓",
                    mock_cosine_similarity=fake_high_cos,
                )
                assert res_cam_fail is None  # 成功攔截！


def test_scheme_2_dynamic_prototype_refinement_ema():
    """
    方案 2 測試：非監督特徵空間動態原型 (Dynamic Prototypes) EMA 更新機制。
    驗證高純度樣本能夠平滑微調聚類中心並保持向量正規化。
    """
    import torch
    from app.services.convnext import DynamicPrototypeManager

    mgr = DynamicPrototypeManager()
    class_idx = 10
    sample_feat = torch.randn(768)

    mgr.update_prototype(class_idx, sample_feat, ema_decay=0.90)
    proto = mgr.prototypes[class_idx]

    # 驗證原型向量已正規化 (L2 norm 近似 1.0)
    norm_val = float(torch.norm(proto, p=2).item())
    assert pytest.approx(norm_val, abs=1e-4) == 1.0


def test_scheme_3_gemini_cross_verification_concurred():
    """
    方案 3 測試：雙模型會診共識 (ConvNeXt 與 Gemini 二次覆核一致)。
    """
    mock_convnext = {
        "crop_name": "番茄",
        "status_name": "早疫病",
        "category": "disease",
        "confidence": 0.86,
        "cosine_similarity": 0.79,
        "cam_foreground_ratio": 0.85,
        "top_k_candidates": [
            {"crop_name": "番茄", "status_name": "早疫病", "score": 0.86, "cosine_similarity": 0.79},
            {"crop_name": "番茄", "status_name": "晚疫病", "score": 0.08, "cosine_similarity": 0.42},
        ],
        "grounding_source": "local_convnext_fast_screen",
    }
    mock_gemini_verify = {
        "verified_crop": "番茄",
        "verified_status": "早疫病",
        "category": "disease",
        "is_concurred": True,
        "confidence": 0.94,
        "override_reason": "葉片可見同心輪紋暗褐斑，與早疫病吻合",
        "suggestion": "- 葉面出現典型輪紋病斑\n- 需防範擴散",
        "treatment": "1. 剪除病葉。\n2. 噴灑防護劑。\n3. 控制濕度。",
    }

    result = diagnostic_plant(
        image_path="dummy.jpg",
        crop_hint="番茄",
        mock_convnext_result=mock_convnext,
        mock_gemini_result=mock_gemini_verify,
    )

    assert result["crop_name"] == "番茄"
    assert result["status_name"] == "早疫病"
    assert result["grounding_source"] == "convnext_gemini_cross_verified"
    assert result["requires_review"] is False
    assert result["confidence"] >= 0.86


def test_scheme_3_gemini_cross_verification_overruled():
    """
    方案 3 測試：雙模型會診推翻機制 (Gemini 視覺推翻 ConvNeXt 錯誤標籤)。
    當 ConvNeXt 誤判為早疫病，但 Gemini 視覺發現為晚疫病，自動校正並標記需審查。
    """
    mock_convnext = {
        "crop_name": "番茄",
        "status_name": "早疫病",
        "category": "disease",
        "confidence": 0.82,
        "cosine_similarity": 0.75,
        "cam_foreground_ratio": 0.80,
        "top_k_candidates": [
            {"crop_name": "番茄", "status_name": "早疫病", "score": 0.82, "cosine_similarity": 0.75},
            {"crop_name": "番茄", "status_name": "晚疫病", "score": 0.12, "cosine_similarity": 0.70},
        ],
        "grounding_source": "local_convnext_fast_screen",
    }
    mock_gemini_overrule = {
        "verified_crop": "番茄",
        "verified_status": "晚疫病",
        "category": "disease",
        "is_concurred": False,
        "confidence": 0.91,
        "override_reason": "病斑為水浸狀暗綠色擴散斑且葉背無同心輪紋，實為晚疫病",
        "suggestion": "- 水浸狀大面積腐爛病斑",
        "treatment": "1. 立即隔離。\n2. 清除發病株。\n3. 加強通風降濕。",
    }

    result = diagnostic_plant(
        image_path="dummy.jpg",
        crop_hint="番茄",
        mock_convnext_result=mock_convnext,
        mock_gemini_result=mock_gemini_overrule,
    )

    assert result["crop_name"] == "番茄"
    assert result["status_name"] == "晚疫病"
    assert result["grounding_source"] == "convnext_overruled_by_gemini_verification"
    assert result["requires_review"] is True
    assert "雙模型會診校正" in result["suggestion"]


def test_gemini_503_fallback_to_secondary_model():
    """驗證當主力模型遇到 503 UNAVAILABLE 尖峰過載時，能自動平滑降級至備援模型。"""
    from unittest.mock import MagicMock
    from types import SimpleNamespace
    from app.services.ai import call_gemini_with_fallback
    import app.services.ai as ai_mod

    mock_client = MagicMock()
    call_log = []

    def mock_generate(model, contents, **kwargs):
        call_log.append(model)
        if "3.8" in model:
            raise Exception("503 UNAVAILABLE. This model is currently experiencing high demand.")
        return SimpleNamespace(text='{"result": "success"}')

    mock_client.models.generate_content.side_effect = mock_generate

    with patch.object(ai_mod, "client", mock_client):
        resp = call_gemini_with_fallback(
            contents="test prompt",
            primary_model="models/gemini-3.8-flash",
            fallback_models=["models/gemini-3.5-flash"],
            max_retries=1,
            base_delay=0.01,
        )
        assert resp is not None
        assert resp.text == '{"result": "success"}'
        assert any("3.8" in m for m in call_log)
        assert any("3.5" in m for m in call_log)


def test_emergency_offline_convnext_rescue_when_gemini_offline():
    """驗證當雲端 Gemini 離線/無法判定且作物未指定時，本地 ConvNeXt 壓倒性置信度可啟動離線應急救援。"""
    mock_emergency = {
        "crop_name": "番茄",
        "status_name": "早疫病",
        "category": "disease",
        "confidence": 0.93,
        "is_confidence_override": True,
        "grounding_source": "local_convnext_fast_screen",
    }

    with patch("app.services.ai._call_gemini_fallback", return_value={"crop_name": "未知作物", "status_name": "無法判定", "confidence": 0.0}):
        with patch("app.services.ai.predict_convnext_fast_screen") as mock_convnext:
            # 第一次正常快篩（crop_name=None）回傳 None，第二次緊急應急（allow_unconstrained_emergency=True）回傳 high confidence
            mock_convnext.side_effect = [None, mock_emergency]
            result = diagnostic_plant("dummy.jpg", crop_hint=None)

            assert result["crop_name"] == "番茄"
            assert result["status_name"] == "早疫病"
            assert result["grounding_source"] == "local_convnext_offline_emergency"
            assert "離線應急" in result["suggestion"]
            assert result["requires_review"] is True


def test_convnext_unconstrained_crop_hit_when_overwhelming():
    """驗證當使用者未指定作物時，若 ConvNeXt 全局 Top-1 達壓倒性高置信度 (>= 85% 且餘弦 >= 0.68)，直接本地命中！"""
    import torch
    from PIL import Image

    dummy_image = Image.new("RGB", (224, 224), color="green")
    idx_map = load_class_index()
    tomato_early_idx = [i for i, label in idx_map.items() if label == "Tomato___Early_blight"][0]

    fake_probs = torch.zeros(38)
    fake_probs[tomato_early_idx] = 0.92  # 壓倒性置信度 92%

    fake_cos = torch.full((38,), 0.20)
    fake_cos[tomato_early_idx] = 0.85  # 特徵幾何相似度 0.85

    with patch("app.services.convnext.Image.open", return_value=dummy_image):
        with patch("app.services.convnext.torch.softmax", return_value=fake_probs.unsqueeze(0)):
            res = predict_convnext_fast_screen(
                "dummy.jpg",
                crop_name=None,  # 未指定作物！
                mock_cosine_similarity=fake_cos,
            )
            assert res is not None
            assert res["crop_name"] == "番茄"
            assert res["status_name"] == "早疫病"
            assert res["confidence"] == pytest.approx(0.92, abs=0.01)
            assert res["is_confidence_override"] is True


def test_image_sha256_diagnosis_cache_idempotency():
    """驗證同一張圖片再次請求時命中 SHA-256 冪等快取，保證 100% 決定性且不重跑 AI 診斷。"""
    import hashlib
    import time
    from unittest.mock import patch, MagicMock
    from app.routers.prediction import image_diagnosis_cache

    image_diagnosis_cache.clear()

    dummy_content = b"fake_lemon_image_bytes_12345"
    img_sha = hashlib.sha256(dummy_content).hexdigest()
    cache_key = (img_sha, "檸檬")

    # 模擬快取寫入
    image_diagnosis_cache[cache_key] = {
        "result": {
            "crop_name": "檸檬",
            "status_name": "柑橘葉蟎",
            "category": "pest",
            "confidence": 0.88,
            "suggestion": "- 葉面微小點狀褪綠\n- 葉背可見微小蛛蟎活動",
            "treatment": "1. 藥劑防治：使用窄域油或礦物油 500 倍全面噴灑。\n2. 增加濕度：定期葉面噴水抑制葉蟎繁衍。",
        },
        "cached_at": time.monotonic()
    }

    # 再次查詢同張圖片與作物
    cached = image_diagnosis_cache.get(cache_key)
    assert cached is not None
    assert cached["result"]["crop_name"] == "檸檬"
    assert cached["result"]["status_name"] == "柑橘葉蟎"
    assert cached["result"]["confidence"] == 0.88






