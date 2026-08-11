import json
import logging
from typing import Any

import requests


logger = logging.getLogger(__name__)

CROP_DATA_URL = (
    "https://data.moa.gov.tw/Service/OpenData/TransService.aspx"
    "?UnitId=LC7YWlenhLuP"
)
MOA_OPEN_API_BASE = "https://data.moa.gov.tw/api/v1"
PEST_DIAGNOSTICS_DATASET = "ImportantAgriculturalPestDiagnosticsType"
TREE_PEST_DATASET = "TreePestInfoType"
REQUEST_TIMEOUT_SECONDS = 30


class MoaDataError(RuntimeError):
    """Raised when an official MOA data response cannot be trusted."""


def _get_json(url: str, params: dict[str, Any] | None = None) -> Any:
    response = requests.get(
        url,
        params=params,
        timeout=REQUEST_TIMEOUT_SECONDS,
        headers={"User-Agent": "plant-diagnosis-reference-sync/1.0"},
    )
    response.raise_for_status()
    return response.json()


def fetch_crop_data() -> list[dict[str, Any]]:
    """Fetch the existing crop catalog without breaking callers on outage."""

    try:
        payload = _get_json(CROP_DATA_URL)
        if not isinstance(payload, list):
            raise MoaDataError("Crop catalog response is not a list")
        return payload
    except (requests.RequestException, ValueError, MoaDataError) as exc:
        logger.error("Unable to fetch MOA crop catalog: %s", exc)
        return []


def fetch_open_dataset(dataset: str, max_pages: int = 100) -> list[dict[str, Any]]:
    """Fetch a paginated MOA OpenAPI dataset with defensive page checks."""

    if dataset not in {PEST_DIAGNOSTICS_DATASET, TREE_PEST_DATASET}:
        raise ValueError(f"Unsupported MOA dataset: {dataset}")

    records: list[dict[str, Any]] = []
    seen_pages: set[str] = set()

    for page in range(1, max_pages + 1):
        url = f"{MOA_OPEN_API_BASE}/{dataset}/"
        try:
            payload = _get_json(url, params={"Page": page})
        except (requests.RequestException, ValueError) as exc:
            raise MoaDataError(f"Unable to fetch {dataset} page {page}: {exc}") from exc

        if not isinstance(payload, dict) or payload.get("RS") != "OK":
            if records:
                logger.warning(
                    "Stopped %s after page %s because the next page was invalid",
                    dataset,
                    page - 1,
                )
                break
            raise MoaDataError(f"Invalid {dataset} response on page {page}")

        page_records = payload.get("Data") or []
        if not isinstance(page_records, list):
            raise MoaDataError(f"Invalid {dataset} data on page {page}")
        if not page_records:
            break

        signature = json.dumps(page_records, ensure_ascii=False, sort_keys=True)
        if signature in seen_pages:
            logger.warning("Stopped %s at repeated page %s", dataset, page)
            break
        seen_pages.add(signature)
        records.extend(record for record in page_records if isinstance(record, dict))

        if not payload.get("Next"):
            break
    else:
        raise MoaDataError(f"{dataset} exceeded the {max_pages}-page safety limit")

    if not records:
        raise MoaDataError(f"{dataset} returned no usable records")
    return records


def fetch_pest_diagnostics() -> list[dict[str, Any]]:
    return fetch_open_dataset(PEST_DIAGNOSTICS_DATASET)


def fetch_tree_pest_info() -> list[dict[str, Any]]:
    return fetch_open_dataset(TREE_PEST_DATASET)


if __name__ == "__main__":
    print(f"Crops: {len(fetch_crop_data())}")
    print(f"Pest diagnostics: {len(fetch_pest_diagnostics())}")
    print(f"Tree cases: {len(fetch_tree_pest_info())}")
