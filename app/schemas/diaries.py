from pydantic import BaseModel, Field
from typing import Optional


class DiaryConfirm(BaseModel):
    """確認日記時，從前端傳送過來的資料模型。"""
    user_note: Optional[str] = Field(None)
    disease_name: str
    gemini_advice: str


class DiaryNoteUpdate(BaseModel):
    """更新日記筆記的資料模型。"""
    user_note: Optional[str] = Field(None)