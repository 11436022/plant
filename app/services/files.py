import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile

from app.core.config import settings


def build_public_image_url(image_path: str) -> str:
    """將檔案路徑(無論絕對或相對)轉為公開網址。"""

    # 1. 從完整的路徑中，只取出檔名部分
    filename = Path(image_path).name

    # 2. 確保基底 URL 結尾沒有斜線，避免產生雙斜線 (e.g. "http://...//uploads")
    base_url = settings.PUBLIC_BASE_URL.rstrip('/')

    # 3. 拼接成一個標準的、可公開存取的 URL
    return f"{base_url}/uploads/{filename}"


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


def ensure_image_upload(file: UploadFile) -> None:
    """限制只接受圖片上傳。"""

    content_type = file.content_type or ""
    if not content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image uploads are supported.")