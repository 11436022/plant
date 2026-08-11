from sqlalchemy.orm import Session

from app.db import models
from app.db.session import SessionLocal
from app.db.models import Crop, User
from app.api_fetch import fetch_crop_data
from app.schemas.feedback import DiagnosisFeedbackCreate


def create_diagnosis_feedback(db: Session, feedback_data: DiagnosisFeedbackCreate, user_id: int) -> models.DiagnosisFeedback:
    """
    將使用者的診斷回饋寫入資料庫。
    採用手動欄位對應，以確保 Pydantic 模型和 SQLAlchemy 模型之間的解耦。
    """
    db_feedback = models.DiagnosisFeedback(
        prediction_id=feedback_data.prediction_id, # <-- 補上遺漏的這一行
        user_id=user_id,
        image_url=feedback_data.image_url,
        original_plant_name=feedback_data.original_plant_name,
        original_disease_name=feedback_data.original_disease_name,
        is_plant_error=feedback_data.is_plant_error,
        is_disease_error=feedback_data.is_disease_error,
        corrected_plant_name=feedback_data.corrected_plant_name,
        corrected_disease_name=feedback_data.corrected_disease_name
    )
    db.add(db_feedback)
    db.commit()
    db.refresh(db_feedback)
    return db_feedback


def get_user_by_username(db: Session, username: str) -> User | None:
    """根據使用者名稱查詢使用者。"""
    return db.query(User).filter(User.username == username).first()


def get_user_by_id(db: Session, user_id: int) -> User | None:
    """根據使用者 ID 查詢使用者。"""
    return db.query(User).filter(User.user_id == user_id).first()



def save_main_crops():
    """將外部 API 回傳的主要作物資料寫入資料庫。"""

    db = SessionLocal()
    data = fetch_crop_data()
    saved = set()

    # 逐筆處理資料，並在同一批資料內避免重複寫入。
    for item in data:
        crop_name = item.get("PLV3_NAME")
        if not crop_name:
            continue

        if crop_name in saved:
            continue

        exists = db.query(Crop).filter(Crop.crop_name == crop_name).first()
        if exists:
            saved.add(crop_name)
            continue

        crop = Crop(crop_name=crop_name)
        db.add(crop)
        saved.add(crop_name)

    db.commit()
    db.close()
    print(f"已寫入或確認 {len(saved)} 種作物。")


if __name__ == "__main__":
    save_main_crops()