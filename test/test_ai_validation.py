import os
import sys
import types
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent
sys.path.append(str(ROOT_DIR))

os.environ.setdefault("GEMINI_API_KEY", "test-key")
os.environ.setdefault("DB_USER", "test")
os.environ.setdefault("DB_PASSWORD", "test")
os.environ.setdefault("DB_HOST", "127.0.0.1")
os.environ.setdefault("DB_NAME", "plant_test")

fake_rag = types.ModuleType("app.services.rag")
fake_rag.search_knowledge_base = lambda *args, **kwargs: ""
sys.modules.setdefault("app.services.rag", fake_rag)

from app.services.ai import UNKNOWN_STATUS_NAME, validate_diagnosis_result


def test_validate_diagnosis_accepts_database_backed_crop_and_disease():
    result = validate_diagnosis_result(
        {
            "crop_name": "番茄",
            "category": "disease",
            "status_name": "晚疫病",
            "confidence": 0.82,
            "suggestion": "- 葉片出現水浸狀斑點",
            "treatment": "1. 移除受害葉片",
        },
        crops=["番茄"],
        diseases=["晚疫病"],
        pests=["蚜蟲"],
    )

    assert result["crop_name"] == "番茄"
    assert result["category"] == "disease"
    assert result["status_name"] == "晚疫病"
    assert result["confidence"] == 0.82


def test_validate_diagnosis_rejects_hallucinated_crop_name():
    result = validate_diagnosis_result(
        {
            "crop_name": "火星番茄",
            "category": "disease",
            "status_name": "晚疫病",
            "confidence": 0.91,
            "suggestion": "- 葉片有斑點",
            "treatment": "1. 使用藥劑",
        },
        crops=["番茄"],
        diseases=["晚疫病"],
        pests=[],
    )

    assert result["category"] == "unknown"
    assert result["status_name"] == UNKNOWN_STATUS_NAME
    assert result["confidence"] <= 0.5


def test_validate_diagnosis_rejects_hallucinated_disease_name():
    result = validate_diagnosis_result(
        {
            "crop_name": "番茄",
            "category": "disease",
            "status_name": "銀河葉斑病",
            "confidence": 0.91,
            "suggestion": "- 葉片有斑點",
            "treatment": "1. 使用藥劑",
        },
        crops=["番茄"],
        diseases=["晚疫病"],
        pests=[],
    )

    assert result["crop_name"] == "番茄"
    assert result["category"] == "unknown"
    assert result["status_name"] == UNKNOWN_STATUS_NAME
    assert result["confidence"] <= 0.5
