import argparse
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

import requests
from PIL import Image
from sqlalchemy import create_engine
from sqlalchemy.orm import Session


ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

TEST_CASES = (
    {
        "id": "tomato-early-blight",
        "source": "PlantVillage",
        "source_url": (
            "https://raw.githubusercontent.com/spMohanty/PlantVillage-Dataset/master/"
            "raw/color/Tomato___Early_blight/"
            "0012b9d2-2130-4a06-a834-b1f3af34f57e___RS_Erly.B%208389.JPG"
        ),
        "expected": {
            "crop_name": "番茄",
            "category": "disease",
            "status_name": "早疫病 (Early Blight)",
        },
    },
    {
        "id": "tomato-late-blight",
        "source": "PlantVillage",
        "source_url": (
            "https://raw.githubusercontent.com/spMohanty/PlantVillage-Dataset/master/"
            "raw/color/Tomato___Late_blight/"
            "0003faa8-4b27-4c65-bf42-6d9e352ca1a5___RS_Late.B%204946.JPG"
        ),
        "expected": {
            "crop_name": "番茄",
            "category": "disease",
            "status_name": "晚疫病 (Late Blight)",
        },
    },
    {
        "id": "tomato-healthy",
        "source": "PlantVillage",
        "source_url": (
            "https://raw.githubusercontent.com/spMohanty/PlantVillage-Dataset/master/"
            "raw/color/Tomato___healthy/"
            "000146ff-92a4-4db6-90ad-8fce2ae4fddd___GH_HL%20Leaf%20259.1.JPG"
        ),
        "expected": {
            "crop_name": "番茄",
            "category": "healthy",
            "status_name": "健康",
        },
    },
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run live Gemini diagnosis checks against labeled internet images"
    )
    parser.add_argument("--download-only", action="store_true")
    parser.add_argument("--minimum-exact", type=int, default=2)
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("artifacts/live-image-results.json"),
    )
    return parser.parse_args()


def download_case(case: dict[str, Any], destination: Path) -> dict[str, Any]:
    response = requests.get(
        case["source_url"],
        timeout=30,
        headers={"User-Agent": "plant-live-image-smoke-test/1.0"},
    )
    response.raise_for_status()
    if not response.content or len(response.content) > 10 * 1024 * 1024:
        raise ValueError(f"Unexpected image size for {case['id']}: {len(response.content)}")

    destination.write_bytes(response.content)
    with Image.open(destination) as image:
        image.verify()
    with Image.open(destination) as image:
        width, height = image.size
        image_format = image.format

    return {
        "bytes": len(response.content),
        "sha256": hashlib.sha256(response.content).hexdigest(),
        "width": width,
        "height": height,
        "format": image_format,
    }


def assess_result(expected: dict[str, str], actual: dict[str, Any] | None) -> dict[str, Any]:
    if not actual:
        return {"outcome": "error", "reason": "diagnosis_service_returned_no_result"}

    exact = all(actual.get(field) == value for field, value in expected.items())
    if exact:
        if expected["category"] == "healthy":
            provenance_valid = (
                actual.get("grounding_source") == "crop_database"
                and actual.get("requires_review") is False
            )
        else:
            reference_fields = (
                actual.get("reference_source"),
                actual.get("reference_url"),
                actual.get("reference_record_id"),
            )
            has_complete_reference = all(reference_fields)
            provenance_valid = (
                actual.get("grounding_source") == "disease_database"
                and (
                    (has_complete_reference and actual.get("requires_review") is False)
                    or (not any(reference_fields) and actual.get("requires_review") is True)
                )
            )
        return {
            "outcome": "exact" if provenance_valid else "unsafe_mismatch",
            "reason": "matched_expected_label" if provenance_valid else "invalid_grounding_metadata",
        }

    if actual.get("category") == "unknown" and actual.get("requires_review") is True:
        return {"outcome": "safe_unknown", "reason": "model_declined_uncertain_image"}

    return {"outcome": "unsafe_mismatch", "reason": "returned_incorrect_known_label"}


def run_live_diagnosis(image_paths: dict[str, Path]) -> list[dict[str, Any]]:
    if not os.getenv("GEMINI_API_KEY"):
        raise RuntimeError("GEMINI_API_KEY is required for live diagnosis")

    os.environ.setdefault("DB_USER", "cloud_test")
    os.environ.setdefault("DB_PASSWORD", "cloud_test")
    os.environ.setdefault("DB_HOST", "127.0.0.1")
    os.environ.setdefault("DB_NAME", "plant_cloud_test")

    from app.db.models import Base
    from app.services.ai import (
        diagnostic_plant,
        get_reference_lists,
        ground_diagnosis_in_database,
    )
    from seed import upsert_reference_data

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = Session(engine)
    try:
        data = json.loads((ROOT_DIR / "data.json").read_text(encoding="utf-8"))
        upsert_reference_data(db, data)
        crops, diseases, pests = get_reference_lists(db)

        results = []
        for case in TEST_CASES:
            model_result = diagnostic_plant(
                str(image_paths[case["id"]]),
                crops,
                diseases,
                pests,
            )
            actual = (
                ground_diagnosis_in_database(model_result, db)
                if model_result
                else None
            )
            results.append(
                {
                    "id": case["id"],
                    "expected": case["expected"],
                    "actual": actual,
                    **assess_result(case["expected"], actual),
                }
            )
        return results
    finally:
        db.close()


def main() -> int:
    args = parse_args()
    if not 0 <= args.minimum_exact <= len(TEST_CASES):
        raise ValueError("--minimum-exact must be between 0 and the number of test cases")

    report: dict[str, Any] = {
        "dataset": "PlantVillage",
        "dataset_url": "https://github.com/spMohanty/PlantVillage-Dataset",
        "cases": [],
    }

    with tempfile.TemporaryDirectory(prefix="plant-live-test-") as temp_dir:
        temp_path = Path(temp_dir)
        image_paths = {}
        for case in TEST_CASES:
            image_path = temp_path / f"{case['id']}.jpg"
            image_paths[case["id"]] = image_path
            metadata = download_case(case, image_path)
            report["cases"].append(
                {
                    "id": case["id"],
                    "source": case["source"],
                    "source_url": case["source_url"],
                    "expected": case["expected"],
                    "image": metadata,
                }
            )

        if not args.download_only:
            diagnoses = {row["id"]: row for row in run_live_diagnosis(image_paths)}
            for case_report in report["cases"]:
                case_report.update(diagnoses[case_report["id"]])

    exact_count = sum(case.get("outcome") == "exact" for case in report["cases"])
    unsafe_count = sum(
        case.get("outcome") in {"unsafe_mismatch", "error"}
        for case in report["cases"]
    )
    report["summary"] = {
        "total": len(TEST_CASES),
        "exact": exact_count,
        "safe_unknown": sum(
            case.get("outcome") == "safe_unknown" for case in report["cases"]
        ),
        "unsafe_or_error": unsafe_count,
        "minimum_exact": args.minimum_exact,
        "download_only": args.download_only,
    }

    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))

    if args.download_only:
        return 0
    return 0 if unsafe_count == 0 and exact_count >= args.minimum_exact else 1


if __name__ == "__main__":
    raise SystemExit(main())
