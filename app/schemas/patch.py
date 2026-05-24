from pydantic import BaseModel, Field
from typing import Optional

class DiaryUpdate(BaseModel):
    crop_name: Optional[str] = Field(None)
    status_name: Optional[str] = Field(None)
    user_note: Optional[str] = Field(None)
    user_corrected_status: Optional[str] = Field(None)


class DiaryConfirm(BaseModel):
    """確認日記時，從前端傳送過來的資料模型。"""
    user_note: Optional[str] = Field(None)
    disease_name: str
    gemini_advice: str