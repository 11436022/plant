import uuid
import io
from dataclasses import dataclass
from pathlib import Path

from fastapi import HTTPException, UploadFile
from PIL import Image, ImageStat, UnidentifiedImageError

from app.core.config import settings


@dataclass(frozen=True)
class FrameMetadata:
    width: int
    height: int
    image_format: str


def validate_image_content(content: bytes, content_type: str | None) -> FrameMetadata:
    """Decode bounded images before any AI call, regardless of upload entry point."""
    mime_formats = {
        "image/jpeg": "JPEG",
        "image/jpg": "JPEG",
        "image/png": "PNG",
        "image/webp": "WEBP",
    }
    allowed_types = set(mime_formats.keys()) | {"image/*", "application/octet-stream"}
    normalized_type = content_type.lower() if content_type else None
    if not content or (normalized_type and normalized_type not in allowed_types):
        raise HTTPException(status_code=400, detail="A nonempty JPEG, PNG, or WebP image is required.")
    if len(content) > settings.WEBCAM_MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="Image exceeds the upload size limit.")
    try:
        with Image.open(io.BytesIO(content)) as image:
            image.verify()
        with Image.open(io.BytesIO(content)) as image:
            width, height = image.size
            image_format = str(image.format or "").upper()
            if image_format not in ("JPEG", "PNG", "WEBP"):
                raise HTTPException(status_code=400, detail="A nonempty JPEG, PNG, or WebP image is required.")
            if width * height > 20_000_000:
                raise HTTPException(status_code=400, detail="Image resolution is too large.")
            if normalized_type in mime_formats and image_format != mime_formats[normalized_type]:
                raise HTTPException(status_code=400, detail="Image format does not match its content type.")
            if width < settings.WEBCAM_MIN_IMAGE_WIDTH or height < settings.WEBCAM_MIN_IMAGE_HEIGHT:
                raise HTTPException(status_code=400, detail=f"Minimum image size is {settings.WEBCAM_MIN_IMAGE_WIDTH}x{settings.WEBCAM_MIN_IMAGE_HEIGHT}.")
            grayscale = image.convert("L")
            grayscale.thumbnail((320, 320))
            if float(ImageStat.Stat(grayscale).stddev[0]) < 5.0:
                raise HTTPException(status_code=422, detail="Image lacks enough visual detail for diagnosis.")
    except (Image.DecompressionBombError, UnidentifiedImageError, OSError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="Image data is invalid or damaged.") from exc
    return FrameMetadata(width, height, image_format)


def build_public_image_url(image_path: str, relative: bool = False) -> str:
    """
    將資料庫中儲存的相對路徑轉為公開網址。
    這個版本更加健壯，不再依賴呼叫者傳遞 folder 參數。
    當 relative=True 時，回傳像 /uploads/xxx.jpg 的相對路徑，適用於瀏覽器 Web 後台渲染；
    當 relative=False 時，拼接 settings.PUBLIC_BASE_URL。
    """
    if not image_path:
        return ""

    # 1. 統一斜線並僅取出檔名部分
    clean_path = str(image_path).replace("\\", "/")
    filename = Path(clean_path).name

    # 2. 根據檔名本身來判斷它屬於哪個資料夾
    #    - 回饋圖片的檔名被設計為以 "feedback_" 開頭
    if filename.startswith("feedback_"):
        folder = "feedback_uploads"
    else:
        # 其他所有情況，都視為診斷紀錄圖片
        folder = "uploads"

    # 3. 相對路徑模式（瀏覽器後台自動相容任意主機與 IP）
    if relative:
        return f"/{folder}/{filename}"

    # 4. 確保基底 URL 結尾沒有斜線並拼接絕對 URL
    base_url = settings.PUBLIC_BASE_URL.rstrip('/')
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
