from typing import Any, Dict

from pydantic import BaseModel


class PlantData(BaseModel):
    """植物辨識結果。"""

    plant_name: str
    confidence: float
    is_healthy: bool


class PredictionResponse(BaseModel):
    """預測 API 回應格式。"""

    status: str
    data: PlantData
    metadata: Dict[str, Any]
