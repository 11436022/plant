from pydantic import BaseModel, Field
from typing import Optional

class DiaryUpdate(BaseModel):
    crop_name: Optional[str] = Field(None)
    status_name: Optional[str] = Field(None)
    user_note: Optional[str] = Field(None)
    user_corrected_status: Optional[str] = Field(None)