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
    plant_tag: Optional[str] = Field(None)  # 🌟 盆栽身分標籤 (如: 陽台1號、客廳2號)
    # Kept optional for older clients; the server never trusts these fields.
    disease_name: Optional[str] = None
    gemini_advice: Optional[str] = None


DiaryPatch = DiaryUpdate
DiaryNoteUpdate = DiaryUpdate
