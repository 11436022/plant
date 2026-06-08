import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile

from app.core.config import settings


def build_public_image_url(image_path: str) -> str:
    """
    將資料庫中儲存的相對路徑轉為公開網址。
    這個版本更加健壯，不再依賴呼叫者傳遞 folder 參數。
    """
    if not image_path:
        return ""

    # 1. 從可能包含路徑的字串中，僅取出檔名部分
    filename = Path(image_path).name

    # 2. 根據檔名本身來判斷它屬於哪個資料夾
    #    - 回饋圖片的檔名被設計為以 "feedback_" 開頭
    if filename.startswith("feedback_"):
        folder = "feedback_uploads"
    else:
        # 其他所有情況，都視為舊的診斷紀錄圖片
        folder = "uploads"

    # 3. 確保基底 URL 結尾沒有斜線
    base_url = settings.PUBLIC_BASE_URL.rstrip('/')

    # 4. 拼接成一個絕對正確的 URL
    return f"{base_url}/{folder}/{filename}"



def create_safe_upload_path(original_name: str) -> Path:
    """產生安全且唯一的上傳檔名。"""

    filename = Path(original_name or "upload.bin").name
    suffix = Path(filename).suffix.lower()
    safe_name = f"{uuid.uuid4().hex}{suffix}"
    file_path = (settings.UPLOAD_DIR / safe_name).resolve()
    upload_root = settings.UPLOAD_DIR.resolve()
    if upload_root not in file_path.parents:
        raise HTTPException(status_code=400, detail="Invalid upload path.")
    return file_path


def create_feedback_image_path(original_name: str) -> Path:
    """為回饋圖片產生安全且唯一的上傳路徑。"""
    filename = Path(original_name or "feedback.bin").name
    suffix = Path(filename).suffix.lower()
    safe_name = f"feedback_{uuid.uuid4().hex}{suffix}"
    
    # 使用 settings.FEEDBACK_UPLOAD_DIR
    file_path = (settings.FEEDBACK_UPLOAD_DIR / safe_name).resolve()
    upload_root = settings.FEEDBACK_UPLOAD_DIR.resolve()

    if upload_root not in file_path.parents:
        raise HTTPException(status_code=400, detail="Invalid feedback image path.")
    return file_path



def ensure_image_upload(file: UploadFile) -> None:
    """限制只接受圖片上傳。"""

    content_type = file.content_type or ""
    if not content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image uploads are supported.")