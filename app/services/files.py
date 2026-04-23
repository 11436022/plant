import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile

from app.core.config import PUBLIC_BASE_URL, UPLOAD_DIR


def build_public_image_url(image_path: str) -> str:
    """將相對圖片路徑轉為公開網址。"""

    clean_path = image_path.replace("\\", "/")
    return f"{PUBLIC_BASE_URL}/{clean_path.lstrip('/')}"


def create_safe_upload_path(original_name: str) -> Path:
    """產生安全且唯一的上傳檔名。"""

    filename = Path(original_name or "upload.bin").name
    suffix = Path(filename).suffix.lower()
    safe_name = f"{uuid.uuid4().hex}{suffix}"
    file_path = (UPLOAD_DIR / safe_name).resolve()
    upload_root = UPLOAD_DIR.resolve()
    if upload_root not in file_path.parents:
        raise HTTPException(status_code=400, detail="Invalid upload path.")
    return file_path


def ensure_image_upload(file: UploadFile) -> None:
    """限制只接受圖片上傳。"""

    content_type = file.content_type or ""
    if not content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image uploads are supported.")
