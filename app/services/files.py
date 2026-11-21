import uuid
import io
from dataclasses import dataclass
from pathlib import Path

from fastapi import HTTPException, UploadFile
from PIL import Image, ImageOps, ImageStat, UnidentifiedImageError

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
    allowed_types = set(mime_formats.keys()) | {"image/*", "application/octet-stream", "binary/octet-stream"}
    normalized_type = content_type.lower() if content_type else None
    if not content or (normalized_type and normalized_type not in allowed_types):
        raise HTTPException(status_code=400, detail="請上傳非空的植物葉片圖片 (JPG / PNG / WebP)。")
    if len(content) > settings.WEBCAM_MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail=f"圖片檔案大小超出限制 (最大 {settings.WEBCAM_MAX_IMAGE_BYTES // (1024*1024)}MB)。")
    try:
        with Image.open(io.BytesIO(content)) as image:
            image.verify()
        with Image.open(io.BytesIO(content)) as image:
            width, height = image.size
            image_format = str(image.format or "").upper()
            if image_format not in ("JPEG", "PNG", "WEBP"):
                raise HTTPException(status_code=400, detail="請上傳標準 JPG、PNG 或 WebP 格式圖片。")
            if width * height > 20_000_000:
                raise HTTPException(status_code=400, detail="圖片解析度過大 (超過 2000 萬像素)，請調整後再試。")
            # 支援手機直拍 (Portrait) 與橫拍 (Landscape)：長邊需達標、短邊不低於 160px
            longer_side = max(width, height)
            shorter_side = min(width, height)
            min_longer = max(settings.WEBCAM_MIN_IMAGE_WIDTH, settings.WEBCAM_MIN_IMAGE_HEIGHT)
            if longer_side < min_longer or shorter_side < 160:
                raise HTTPException(
                    status_code=400,
                    detail=f"圖片解析度過低（至少需 {settings.WEBCAM_MIN_IMAGE_WIDTH}×{settings.WEBCAM_MIN_IMAGE_HEIGHT}），請上傳清晰的葉片照片以利 AI 辨識。"
                )
            grayscale = image.convert("L")
            grayscale.thumbnail((320, 320))
            if float(ImageStat.Stat(grayscale).stddev[0]) < 5.0:
                raise HTTPException(status_code=422, detail="圖片對比度過低或過於模糊，缺乏足夠視覺細節進行 AI 診斷。")
    except HTTPException:
        raise
    except (Image.DecompressionBombError, UnidentifiedImageError, OSError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="圖片格式無效或檔案損壞，請上傳有效的 JPG、PNG 或 WebP 影像。") from exc
    return FrameMetadata(width, height, image_format)


def prepare_optimized_image_for_ai(
    image_source: str | Path | Image.Image | bytes,
    max_dimension: int = 1024,
    quality: int = 85,
) -> Image.Image:
    """
    將送往 Gemini 或深度學習模型的影像進行最適化降採樣與壓縮：
    1. EXIF 方向自動矯正 (ImageOps.exif_transpose)，避免手機直拍橫拍視角顛倒。
    2. 強制統一為 RGB 色彩模式（移除 Alpha 透明通道雜訊）。
    3. 若影像長邊超過 max_dimension (預設 1024px)，以 LANCZOS 高精度等比縮放，確保病斑紋理邊緣完整保留。
    4. 透過 BytesIO 壓製為標準 JPEG，將傳輸體積從 8MB~15MB 壓縮至 ~150KB-300KB (減少 90%~95% 傳輸時間)。
    """
    if isinstance(image_source, (str, Path)):
        img = Image.open(str(image_source))
    elif isinstance(image_source, bytes):
        img = Image.open(io.BytesIO(image_source))
    elif isinstance(image_source, Image.Image):
        img = image_source
    else:
        raise ValueError("Unsupported image source type")

    try:
        img = ImageOps.exif_transpose(img)
    except Exception:
        pass

    if img.mode != "RGB":
        img = img.convert("RGB")

    w, h = img.size
    if max(w, h) > max_dimension:
        scale = max_dimension / float(max(w, h))
        new_w = max(1, int(round(w * scale)))
        new_h = max(1, int(round(h * scale)))
        img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=quality, optimize=True)
    buffer.seek(0)
    return Image.open(buffer)


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
