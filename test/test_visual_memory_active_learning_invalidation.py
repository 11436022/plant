import io
import time
import pytest
from PIL import Image
import torch
from unittest.mock import patch

from app.routers.prediction import image_diagnosis_cache, clear_image_diagnosis_cache, predict_plant_status
from app.services.visual_memory import visual_memory
from app.services.ai import diagnostic_plant


def test_active_learning_feedback_invalidates_cache_and_hits_visual_memory():
    """
    驗證使用者提報回饋並校正後，重複上傳同一張影像不會被舊的錯誤快取攔截，
    而是正確穿透快取並由視覺特徵記憶庫直接採納專家真值！
    """
    # 1. 建立測試假影像
    img = Image.new("RGB", (224, 224), color=(100, 180, 80))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    img_bytes = buf.getvalue()

    # 模擬快取中曾有舊的錯誤診斷 (例如舊預測是 '黑腐病')
    clear_image_diagnosis_cache()
    import hashlib
    img_hash = hashlib.sha256(img_bytes).hexdigest()
    cache_key = (img_hash, "")

    image_diagnosis_cache[cache_key] = {
        "result": {
            "crop_name": "番茄",
            "status_name": "黑腐病",  # 錯誤舊診斷
            "category": "disease",
            "confidence": 0.70,
            "suggestion": "舊錯誤建議",
            "treatment": "舊錯誤處方",
        },
        "cached_at": time.monotonic() - 10,
        "cached_at_datetime": visual_memory.last_sync_time,  # 舊時間
    }

    assert cache_key in image_diagnosis_cache

    # 2. 模擬農業專家在後台校正並重建視覺記憶庫 (修正為 '炭疽病')
    # 手動在記憶庫注入一個模擬專家樣本 (特徵向量與當前圖片完全相同，相似度 1.0)
    fake_emb = torch.randn(768)
    fake_emb = fake_emb / torch.norm(fake_emb, p=2)

    with patch.object(visual_memory, "extract_image_embedding", return_value=fake_emb):
        visual_memory.embeddings = fake_emb.unsqueeze(0)
        visual_memory.records = [{
            "unique_key": "feedback_999",
            "feedback_id": 999,
            "crop_name": "番茄",
            "status_name": "炭疽病",  # 專家校正真值！
            "image_url": "dummy.jpg",
            "source": "feedback",
        }]
        # 觸發更新
        from datetime import datetime
        visual_memory.last_sync_time = datetime.now()
        clear_image_diagnosis_cache()

    # 驗證快取已被清空
    assert len(image_diagnosis_cache) == 0

    # 3. 再次執行診斷（模擬使用者重新上傳同一張圖片）
    with patch.object(visual_memory, "extract_image_embedding", return_value=fake_emb):
        res = diagnostic_plant(
            image_path="dummy.jpg",
            crop_hint=None,
            mock_convnext_result={"crop_name": "番茄", "status_name": "黑腐病", "confidence": 0.75, "category": "disease"}
        )

    # 驗證：不再回答舊的 '黑腐病'，而是精準命中專家真值 '炭疽病'！
    assert res["crop_name"] == "番茄"
    assert res["status_name"] == "炭疽病"
    assert res["grounding_source"] == "visual_memory_expert_verified"
    assert "主動學習自適應命中" in res["suggestion"]
    print("\n[TEST PASS] 重複上傳成功穿透舊快取，並由 Visual Memory 採納專家真值！")
