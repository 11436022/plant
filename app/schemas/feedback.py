from pydantic import BaseModel, Field
from typing import Optional

class DiagnosisFeedbackCreate(BaseModel):
    """
    用於接收使用者診斷回饋的 Pydantic 模型。
    """
    prediction_id: str = Field(..., description="關聯的預測 ID，用於查找原始圖片。")
    image_url: Optional[str] = Field(None, description="發生錯誤的診斷圖片 URL (將由後端覆寫)。")
    original_plant_name: Optional[str] = Field(None, description="AI 原始判斷的植物名稱。")
    original_disease_name: Optional[str] = Field(None, description="AI 原始判斷的疾病名稱。")
    
    # 使用者回饋的錯誤類型
    is_plant_error: bool = Field(False, description="使用者是否回報植物名稱錯誤。")
    is_disease_error: bool = Field(False, description="使用者是否回報疾病名稱錯誤。")
    
    # 使用者提供的正確資訊 (可選)
    corrected_plant_name: Optional[str] = Field(None, description="使用者修正的植物名稱。")
    corrected_disease_name: Optional[str] = Field(None, description="使用者修正的疾病名稱。")

class DiagnosisFeedbackResponse(BaseModel):
    """
    回饋成功後的回應模型。
    """
    id: int

    class Config:
        from_attributes = True