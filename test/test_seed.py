import os

from sqlalchemy import create_engine
from sqlalchemy.orm import Session


os.environ.setdefault("DB_USER", "test")
os.environ.setdefault("DB_PASSWORD", "test")
os.environ.setdefault("DB_HOST", "127.0.0.1")
os.environ.setdefault("DB_NAME", "plant_test")

from app.db.models import Base, Crop, Disease, Pest
from seed import upsert_reference_data


def test_upsert_reference_data_updates_without_duplicates_and_skips_unlinked_rows():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = Session(engine)
    data = {
        "crops": [{"crop_name": "番茄", "crop_name_en": "Tomato"}],
        "diseases": [
            {
                "crop_name": "番茄",
                "disease_name": "晚疫病",
                "description": "初始症狀",
                "treatment": "初始處置",
                "source_name": "農業部",
                "source_url": "https://data.moa.gov.tw/disease/1",
                "source_record_id": "disease-1",
            },
            {
                "crop_name": None,
                "disease_name": "未綁定病害",
                "description": "不可用",
                "treatment": "不可用",
            },
        ],
        "pests": [
            {
                "crop_name": "番茄",
                "pest_name": "粉蝨",
                "description": "危害葉片",
                "treatment": "請專業確認",
            }
        ],
    }

    first = upsert_reference_data(db, data)

    assert first["crops"]["created"] == 1
    assert first["diseases"] == {
        "created": 1,
        "updated": 0,
        "unchanged": 0,
        "skipped": 1,
    }
    assert first["pests"]["created"] == 1

    data["diseases"][0]["description"] = "更新後症狀"
    second = upsert_reference_data(db, data)

    assert second["diseases"]["updated"] == 1
    assert db.query(Crop).count() == 1
    assert db.query(Disease).count() == 1
    assert db.query(Pest).count() == 1
    disease = db.query(Disease).one()
    assert disease.description == "更新後症狀"
    assert disease.source_record_id == "disease-1"
    db.close()
