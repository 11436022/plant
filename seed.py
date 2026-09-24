import json
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.db import models
from app.db.session import SessionLocal


DEFAULT_DATA_PATH = Path(__file__).with_name("data.json")
REFERENCE_FIELDS = (
    "description",
    "treatment",
    "source_name",
    "source_url",
    "source_record_id",
)


def _clean(value: Any) -> str:
    return str(value or "").strip()


def _apply_values(record: Any, row: dict[str, Any], fields: tuple[str, ...]) -> bool:
    changed = False
    for field in fields:
        if field not in row:
            continue
        value = row[field]
        if getattr(record, field) != value:
            setattr(record, field, value)
            changed = True
    return changed


def _upsert_crops(
    db: Session,
    rows: list[dict[str, Any]],
) -> tuple[dict[str, models.Crop], dict[str, int]]:
    crops = {crop.crop_name: crop for crop in db.query(models.Crop).all()}
    summary = {"created": 0, "updated": 0, "unchanged": 0, "skipped": 0}

    for row in rows:
        crop_name = _clean(row.get("crop_name"))
        if not crop_name:
            summary["skipped"] += 1
            continue

        crop = crops.get(crop_name)
        if crop is None:
            crop = models.Crop(
                crop_name=crop_name,
                crop_name_en=row.get("crop_name_en"),
            )
            db.add(crop)
            crops[crop_name] = crop
            summary["created"] += 1
            continue

        crop_name_en = row.get("crop_name_en")
        if crop_name_en and crop.crop_name_en != crop_name_en:
            crop.crop_name_en = crop_name_en
            summary["updated"] += 1
        else:
            summary["unchanged"] += 1

    db.flush()
    return crops, summary


def _upsert_references(
    db: Session,
    rows: list[dict[str, Any]],
    crops: dict[str, models.Crop],
    model: type[models.Disease] | type[models.Pest],
    name_field: str,
) -> dict[str, int]:
    summary = {"created": 0, "updated": 0, "unchanged": 0, "skipped": 0}
    name_column = getattr(model, name_field)

    for row in rows:
        crop_name = _clean(row.get("crop_name"))
        record_name = _clean(row.get(name_field))
        crop = crops.get(crop_name)
        if not crop or not record_name:
            summary["skipped"] += 1
            continue

        record = (
            db.query(model)
            .filter(name_column == record_name, model.crop_id == crop.crop_id)
            .first()
        )
        if record is None:
            values = {
                field: row[field]
                for field in REFERENCE_FIELDS
                if field in row
            }
            values.update({"crop_id": crop.crop_id, name_field: record_name})
            db.add(model(**values))
            summary["created"] += 1
        elif _apply_values(record, row, REFERENCE_FIELDS):
            summary["updated"] += 1
        else:
            summary["unchanged"] += 1

    return summary


def upsert_reference_data(db: Session, data: dict[str, Any]) -> dict[str, dict[str, int]]:
    crops, crop_summary = _upsert_crops(db, data.get("crops", []))
    disease_summary = _upsert_references(
        db,
        data.get("diseases", []),
        crops,
        models.Disease,
        "disease_name",
    )
    pest_summary = _upsert_references(
        db,
        data.get("pests", []),
        crops,
        models.Pest,
        "pest_name",
    )
    db.commit()
    return {
        "crops": crop_summary,
        "diseases": disease_summary,
        "pests": pest_summary,
    }


def seed_data(data_path: Path = DEFAULT_DATA_PATH) -> dict[str, dict[str, int]]:
    data = json.loads(data_path.read_text(encoding="utf-8"))
    db = SessionLocal()
    try:
        return upsert_reference_data(db, data)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print(json.dumps(seed_data(), ensure_ascii=False, indent=2))
