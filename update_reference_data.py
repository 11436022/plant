import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from app.api_fetch import fetch_pest_diagnostics, fetch_tree_pest_info


PEST_SOURCE_NAME = "農業部重要農業害蟲診斷圖鑑"
TREE_SOURCE_NAME = "農業部樹木病蟲害診斷案例"
PEST_SOURCE_URL = "https://data.moa.gov.tw/api/v1/ImportantAgriculturalPestDiagnosticsType/"
TREE_SOURCE_URL = "https://data.moa.gov.tw/api/v1/TreePestInfoType/"
MANAGED_SOURCE_NAMES = {PEST_SOURCE_NAME, TREE_SOURCE_NAME}
TRUSTED_TREE_METHODS = {"樣本檢驗", "現地診察", "現場診察"}
CHEMICAL_INSTRUCTION_MARKERS = (
    "%",
    "％",
    "稀釋",
    "倍",
    "乳劑",
    "水懸劑",
    "可濕性",
    "粒劑",
    "農藥",
    "藥劑",
    "施藥",
    "噴灑",
)
HARM_FIELDS = (
    ("Harm_Root", "根部"),
    ("Harm_Stem", "莖部"),
    ("Harm_leaf", "葉片"),
    ("Harm_Flower", "花"),
    ("Harm_Fruit", "果實"),
    ("Harm_Plant", "全株"),
)


def _clean(value: Any, limit: int | None = None) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if limit is not None:
        text = text[:limit].rstrip()
    return text


def _crop_names(value: Any) -> list[str]:
    raw_name = _clean(value)
    names = {
        _clean(name, 100)
        for name in re.split(r"[、，,./／;；]+", raw_name)
        if _clean(name) not in {"", "不明", "不詳", "未知"}
    }
    return sorted(names)


def _stable_record_id(prefix: str, *parts: str) -> str:
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:24]
    return f"{prefix}-{digest}"


def _safe_treatment(advice: Any) -> str:
    cleaned_advice = _clean(advice, 1600)
    current_label_warning = (
        "請由農業專業人員確認，並依農業部現行核准資訊與產品標示處理；"
        "請勿只依影像辨識結果自行施藥。"
    )
    if not cleaned_advice:
        return f"官方資料未提供可直接套用的處置方式。{current_label_warning}"
    if any(marker in cleaned_advice for marker in CHEMICAL_INSTRUCTION_MARKERS):
        return (
            "此官方歷史案例含特定藥劑、濃度或施用方式，可能不符合目前核准用法，"
            f"系統不直接回傳該舊處方。{current_label_warning}"
        )
    return f"官方歷史案例建議：{cleaned_advice} {current_label_warning}"


def _build_pest_records(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    records: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        pest_name = _clean(row.get("PestName_Ch"), 100)
        source_record_id = _clean(row.get("ID"), 128)
        if not pest_name or not source_record_id:
            continue

        harmed_parts = [label for field, label in HARM_FIELDS if _clean(row.get(field))]
        part_text = "、".join(harmed_parts) if harmed_parts else "植株"
        scientific_name = _clean(row.get("PestName_Scientific"), 200)
        other = _clean(row.get("Other"), 500)

        for crop_name in _crop_names(row.get("Crop_Name")):
            description = f"農業部診斷圖鑑記錄：{pest_name}可危害{crop_name}的{part_text}。"
            if scientific_name:
                description += f" 學名：{scientific_name}。"
            if other:
                description += f" 補充：{other}"

            records[(crop_name, pest_name)] = {
                "crop_name": crop_name,
                "pest_name": pest_name,
                "description": _clean(description, 2000),
                "treatment": _safe_treatment(None),
                "source_name": PEST_SOURCE_NAME,
                "source_url": _clean(row.get("Image"), 2048) or PEST_SOURCE_URL,
                "source_record_id": source_record_id,
            }
    return [records[key] for key in sorted(records)]


def _tree_row_quality(row: dict[str, Any]) -> tuple[int, int]:
    method = _clean(row.get("DiagnosisMethod"))
    method_rank = 2 if method == "樣本檢驗" else 1
    detail_length = len(_clean(row.get("symptom"))) + len(_clean(row.get("Injury_Description")))
    return method_rank, detail_length


def _build_tree_records(
    rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    selected: dict[tuple[str, str, str], dict[str, Any]] = {}
    for row in rows:
        injury_type = _clean(row.get("Injury_Type"))
        method = _clean(row.get("DiagnosisMethod"))
        case_name = _clean(row.get("CaseName"), 100)
        if injury_type not in {"病害", "蟲害"} or method not in TRUSTED_TREE_METHODS or not case_name:
            continue

        for crop_name in _crop_names(row.get("TreeType")):
            key = (injury_type, crop_name, case_name)
            if key not in selected or _tree_row_quality(row) > _tree_row_quality(selected[key]):
                selected[key] = row

    diseases: list[dict[str, Any]] = []
    pests: list[dict[str, Any]] = []
    for (injury_type, crop_name, case_name), row in sorted(selected.items()):
        symptom = _clean(row.get("symptom"), 900)
        injury_description = _clean(row.get("Injury_Description"), 900)
        details = []
        if symptom:
            details.append(f"症狀：{symptom}")
        if injury_description and injury_description != symptom:
            details.append(f"受害描述：{injury_description}")
        details.append(f"確認方式：{_clean(row.get('DiagnosisMethod'))}")
        description = "；".join(details) + "。"
        source_record_id = _stable_record_id("tree", injury_type, crop_name, case_name)
        common = {
            "crop_name": crop_name,
            "description": _clean(description, 2000),
            "treatment": _safe_treatment(row.get("Advice")),
            "source_name": TREE_SOURCE_NAME,
            "source_url": TREE_SOURCE_URL,
            "source_record_id": source_record_id,
        }
        if injury_type == "病害":
            diseases.append({**common, "disease_name": case_name})
        else:
            pests.append({**common, "pest_name": case_name})
    return diseases, pests


def _merge_records(
    existing: list[dict[str, Any]],
    official: list[dict[str, Any]],
    name_field: str,
) -> list[dict[str, Any]]:
    retained = [row for row in existing if row.get("source_name") not in MANAGED_SOURCE_NAMES]
    known_keys = {
        (_clean(row.get("crop_name")), _clean(row.get(name_field)))
        for row in retained
    }
    for row in official:
        key = (_clean(row.get("crop_name")), _clean(row.get(name_field)))
        if key in known_keys:
            continue
        retained.append(row)
        known_keys.add(key)
    return retained


def build_reference_data(
    existing: dict[str, Any],
    pest_rows: list[dict[str, Any]],
    tree_rows: list[dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, int]]:
    official_pests = _build_pest_records(pest_rows)
    official_diseases, tree_pests = _build_tree_records(tree_rows)
    official_pests.extend(tree_pests)

    diseases = _merge_records(existing.get("diseases", []), official_diseases, "disease_name")
    pests = _merge_records(existing.get("pests", []), official_pests, "pest_name")

    crops = list(existing.get("crops", []))
    crop_names = {_clean(crop.get("crop_name")) for crop in crops}
    referenced_crop_names = {
        _clean(row.get("crop_name"))
        for row in diseases + pests
        if _clean(row.get("crop_name"))
    }
    for crop_name in sorted(referenced_crop_names - crop_names):
        crops.append({"crop_name": crop_name, "crop_name_en": None})

    result = dict(existing)
    result["crops"] = crops
    result["diseases"] = diseases
    result["pests"] = pests
    result["reference_sync"] = {
        "policy": "official_records_only; historical chemical instructions suppressed",
        "pest_source": PEST_SOURCE_NAME,
        "tree_source": TREE_SOURCE_NAME,
        "pest_rows_received": len(pest_rows),
        "tree_rows_received": len(tree_rows),
    }
    summary = {
        "crops": len(crops),
        "diseases": len(diseases),
        "pests": len(pests),
        "official_diseases": len(official_diseases),
        "official_pests": len(official_pests),
    }
    return result, summary


def serialize_reference_data(data: dict[str, Any]) -> str:
    """Keep list records on one line so sync diffs remain reviewable."""

    lines = ["{"]
    items = list(data.items())
    for item_index, (key, value) in enumerate(items):
        suffix = "," if item_index < len(items) - 1 else ""
        encoded_key = json.dumps(key, ensure_ascii=False)
        if isinstance(value, list):
            lines.append(f"  {encoded_key}: [")
            for row_index, row in enumerate(value):
                row_suffix = "," if row_index < len(value) - 1 else ""
                encoded_row = json.dumps(row, ensure_ascii=False)
                lines.append(f"    {encoded_row}{row_suffix}")
            lines.append(f"  ]{suffix}")
        else:
            encoded_value = json.dumps(value, ensure_ascii=False)
            lines.append(f"  {encoded_key}: {encoded_value}{suffix}")
    lines.append("}")
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Update diagnosis reference data from official MOA APIs")
    parser.add_argument("--input", type=Path, default=Path("data.json"))
    parser.add_argument("--output", type=Path, default=Path("data.json"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    existing = json.loads(args.input.read_text(encoding="utf-8"))
    updated, summary = build_reference_data(
        existing,
        fetch_pest_diagnostics(),
        fetch_tree_pest_info(),
    )
    args.output.write_text(serialize_reference_data(updated), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
