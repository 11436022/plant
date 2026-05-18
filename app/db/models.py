from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class Crop(Base):
    """作物資料表。"""

    __tablename__ = "crop"

    crop_id = Column(Integer, primary_key=True, index=True)
    crop_name = Column(String(100), unique=True, nullable=False)
    crop_name_en = Column(String(100))

    diseases = relationship("Disease", back_populates="crop")
    pests = relationship("Pest", back_populates="crop")


class Disease(Base):
    """病害資料表。"""

    __tablename__ = "disease"

    disease_id = Column(Integer, primary_key=True, index=True)
    crop_id = Column(Integer, ForeignKey("crop.crop_id"))
    disease_name = Column(String(100))
    description = Column(Text)
    treatment = Column(Text)

    crop = relationship("Crop", back_populates="diseases")


class Pest(Base):
    """蟲害資料表。"""

    __tablename__ = "pests"

    pest_id = Column(Integer, primary_key=True, index=True)
    crop_id = Column(Integer, ForeignKey("crop.crop_id"))
    pest_name = Column(String(100), nullable=False)
    description = Column(Text)
    treatment = Column(Text)

    crop = relationship("Crop", back_populates="pests")


class User(Base):
    """使用者資料表。"""

    __tablename__ = "user"

    user_id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    email = Column(String(100), unique=True, nullable=True)
    full_name = Column(String(50))
    role = Column(String(20), nullable=False, default="user")
    # 新註冊帳號需要先驗證信箱；既有資料庫則由 migration 與啟動修補補齊欄位。
    is_email_verified = Column(Boolean, nullable=False, default=True)
    email_verified_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    plant_diary = relationship("PlantDiary", back_populates="user")


class PlantDiary(Base):
    """植物診斷日誌資料表。"""

    __tablename__ = "plant_diary"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user.user_id"))
    crop_id = Column(Integer, ForeignKey("crop.crop_id"))
    status_name = Column(String(100), nullable=True)
    image_url = Column(String(2048))
    disease_id = Column(Integer, ForeignKey("disease.disease_id"), nullable=True)
    pest_id = Column(Integer, ForeignKey("pests.pest_id"), nullable=True)
    confidence = Column(Float)
    suggestion = Column(Text)
    treatment = Column(Text)
    user_note = Column(Text)
    user_corrected_status = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="plant_diary")
    crop = relationship("Crop")
    disease = relationship("Disease")
    pest = relationship("Pest")