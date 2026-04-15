from pydantic import BaseModel
from typing import Dict, Any

class PlantData(BaseModel):
    plant_name: str
    confidence: float
    is_healthy: bool

class PredictionResponse(BaseModel):
    status: str
    data: PlantData
    metadata: Dict[str, Any]