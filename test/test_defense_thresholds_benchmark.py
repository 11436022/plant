# -*- coding: utf-8 -*-
"""
test_defense_thresholds_benchmark.py
針對 R02 五重防禦架構 7 大關鍵門檻的自動化單元測試套件：
- 門檻 1: 影像方差 5.0 (壞幀攔截)
- 門檻 2: ConvNeXt 信心度 75% (監督式放行)
- 門檻 3: 特徵餘弦相似度 0.68 (非監督 OOD 攔截)
- 門檻 4: Grad-CAM 前景對齊率 35% (弱監督空間注意力)
- 門檻 5: Gemini 常規確診 65%
- 門檻 6: Gemini 健康非對稱門檻 85%
- 門檻 7: Webcam 連續 3 幀 >= 80% 時序平滑共識
"""

import io
from datetime import datetime, timezone
from PIL import Image, ImageDraw
import pytest
import torch
from unittest.mock import patch

from app.core.config import settings
from app.services.files import validate_image_content
from app.services.convnext import (
    load_class_index,
    predict_convnext_fast_screen,
)
from app.services.ai import validate_diagnosis_result
from app.services.webcam import AlertConsensusTracker


def test_threshold_1_sharpness_laplacian_filtering():
    """門檻 1：模糊/純色幀 (方差 < 5.0) 攔截，紋理清晰幀 (方差 >= 5.0) 放行。"""
    blank = Image.new("RGB", (320, 240), color="#808080")
    b_buf = io.BytesIO()
    blank.save(b_buf, format="JPEG")

    sharp = Image.new("RGB", (320, 240), color="#808080")
    draw = ImageDraw.Draw(sharp)
    for x in range(0, 320, 20):
        draw.line((x, 0, x, 240), fill="#101010", width=4)
    s_buf = io.BytesIO()
    sharp.save(s_buf, format="JPEG")

    # 模糊影像拋出 422
    with pytest.raises(Exception):
        validate_image_content(b_buf.getvalue(), "image/jpeg")

    # 清晰影像成功放行
    meta = validate_image_content(s_buf.getvalue(), "image/jpeg")
    assert meta.width == 320


def test_threshold_2_convnext_confidence_cut():
    """門檻 2：ConvNeXt >= 75% 命中，< 75% 轉交 Gemini。"""
    dummy_img = Image.new("RGB", (224, 224), color="green")
    idx_map = load_class_index()
    tomato_idx = [i for i, lbl in idx_map.items() if lbl == "Tomato___Early_blight"][0]

    probs_high = torch.zeros(38)
    probs_high[tomato_idx] = 0.78
    probs_low = torch.zeros(38)
    probs_low[tomato_idx] = 0.65
    cos_dummy = torch.full((38,), 0.80)

    with patch("app.services.convnext.Image.open", return_value=dummy_img):
        with patch("app.services.convnext.torch.softmax", return_value=probs_high.unsqueeze(0)):
            res_pass = predict_convnext_fast_screen("dummy.jpg", crop_name="番茄", mock_cosine_similarity=cos_dummy)
            assert res_pass is not None
            assert res_pass["status_name"] == "早疫病"
            assert res_pass["confidence"] == pytest.approx(0.78, abs=1e-4)

        with patch("app.services.convnext.torch.softmax", return_value=probs_low.unsqueeze(0)):
            res_fail = predict_convnext_fast_screen("dummy.jpg", crop_name="番茄", mock_cosine_similarity=cos_dummy)
            assert res_fail is None


def test_threshold_3_cosine_similarity_ood_boundary():
    """門檻 3：餘弦相似度 >= 0.68 放行，< 0.68 (OOD 異物/果實) 攔截。"""
    dummy_img = Image.new("RGB", (224, 224), color="green")
    idx_map = load_class_index()
    tomato_idx = [i for i, lbl in idx_map.items() if lbl == "Tomato___Early_blight"][0]

    probs = torch.zeros(38)
    probs[tomato_idx] = 0.95

    cos_pass = torch.full((38,), 0.20)
    cos_pass[tomato_idx] = 0.75
    cos_ood = torch.full((38,), 0.20)
    cos_ood[tomato_idx] = 0.52

    with patch("app.services.convnext.Image.open", return_value=dummy_img):
        with patch("app.services.convnext.torch.softmax", return_value=probs.unsqueeze(0)):
            res_pass = predict_convnext_fast_screen("dummy.jpg", crop_name="番茄", mock_cosine_similarity=cos_pass)
            assert res_pass is not None

            res_ood = predict_convnext_fast_screen("dummy.jpg", crop_name="番茄", mock_cosine_similarity=cos_ood)
            assert res_ood is None


def test_threshold_4_grad_cam_foreground_overlap():
    """門檻 4：Grad-CAM 前景對齊率 >= 35% 放行，< 35% 雜訊攔截。"""
    dummy_img = Image.new("RGB", (224, 224), color="green")
    idx_map = load_class_index()
    tomato_idx = [i for i, lbl in idx_map.items() if lbl == "Tomato___Early_blight"][0]

    probs = torch.zeros(38)
    probs[tomato_idx] = 0.88
    cos = torch.full((38,), 0.80)

    with patch("app.services.convnext.Image.open", return_value=dummy_img):
        with patch("app.services.convnext.torch.softmax", return_value=probs.unsqueeze(0)):
            with patch("app.services.convnext.compute_cam_foreground_alignment", return_value=0.75):
                res_pass = predict_convnext_fast_screen("dummy.jpg", crop_name="番茄", mock_cosine_similarity=cos)
                assert res_pass is not None

            with patch("app.services.convnext.compute_cam_foreground_alignment", return_value=0.15):
                res_fail = predict_convnext_fast_screen("dummy.jpg", crop_name="番茄", mock_cosine_similarity=cos)
                assert res_fail is None


def test_threshold_5_gemini_diagnosis_confidence():
    """門檻 5：Gemini 確診 >= 65% 放行，< 65% 降級為無法判定。"""
    crops = ["番茄"]
    diseases = ["晚疫病"]

    data_pass = {"crop_name": "番茄", "category": "disease", "status_name": "晚疫病", "confidence": 0.70}
    res_pass = validate_diagnosis_result(data_pass, crops, diseases, [])
    assert res_pass["status_name"] == "晚疫病"

    data_fail = {"crop_name": "番茄", "category": "disease", "status_name": "晚疫病", "confidence": 0.55}
    res_fail = validate_diagnosis_result(data_fail, crops, diseases, [])
    assert res_fail["category"] == "unknown"
    assert res_fail["status_name"] == "無法判定"


def test_threshold_6_gemini_asymmetric_healthy():
    """門檻 6：Gemini 健康非對稱門檻 >= 85% 確診，< 85% 保守攔截為無法判定。"""
    crops = ["番茄"]
    diseases = ["晚疫病"]

    data_pass = {"crop_name": "番茄", "category": "healthy", "status_name": "健康", "confidence": 0.88}
    res_pass = validate_diagnosis_result(data_pass, crops, diseases, [])
    assert res_pass["category"] == "healthy"

    data_fail = {"crop_name": "番茄", "category": "healthy", "status_name": "健康", "confidence": 0.75}
    res_fail = validate_diagnosis_result(data_fail, crops, diseases, [])
    assert res_fail["category"] == "unknown"


def test_threshold_7_webcam_temporal_consensus():
    """門檻 7：Webcam 連續 3 幀 >= 80% 達成共識警報，抗偶發跳幀。"""
    tracker = AlertConsensusTracker()
    now = datetime(2026, 7, 20, tzinfo=timezone.utc)
    diag_high = {
        "crop_name": "番茄",
        "category": "disease",
        "status_name": "晚疫病",
        "confidence": 0.85,
        "grounding_source": "disease_database",
        "requires_review": False,
    }
    diag_low = {
        "crop_name": "番茄",
        "category": "disease",
        "status_name": "晚疫病",
        "confidence": 0.65,
        "grounding_source": "disease_database",
        "requires_review": False,
    }

    assert tracker.evaluate(99, diag_high, now)["triggered"] is False
    assert tracker.evaluate(99, diag_high, now)["triggered"] is False
    assert tracker.evaluate(99, diag_high, now)["triggered"] is True

    tracker_reset = AlertConsensusTracker()
    tracker_reset.evaluate(100, diag_high, now)
    tracker_reset.evaluate(100, diag_high, now)
    r_reset = tracker_reset.evaluate(100, diag_low, now)
    assert r_reset["streak"] == 0

