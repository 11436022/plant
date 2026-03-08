from sqlalchemy import Column, Integer, String, Text, Float,ForeignKey,DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database import Base

class Crop(Base):
    __tablename__ = "crop"
    crop_id = Column(Integer, primary_key=True, index=True)
    crop_name = Column(String(100), unique=True, nullable=False)
    crop_name_en = Column(String(100))
    diseases = relationship("Disease", back_populates="crop")
    pests = relationship("Pest", back_populates="crop")

class Disease(Base):
    __tablename__ = "disease"
    disease_id = Column(Integer, primary_key=True, index=True)
    crop_id = Column(Integer, ForeignKey("crop.crop_id"))
    disease_name = Column(String(100), nullable=False)
    description = Column(Text)
    crop = relationship("Crop", back_populates="diseases")
    
class Pest(Base):
    __tablename__ = "pests"
    pest_id = Column(Integer, primary_key=True, index=True)
    crop_id = Column(Integer, ForeignKey("crop.crop_id"))
    pest_name = Column(String(100), nullable=False)
    description = Column(Text)
    crop = relationship("Crop", back_populates="pests")    
class User(Base):
    __tablename__ = "user"
    user_id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    email = Column(String(100), unique=True, nullable=True)
    full_name = Column(String(50))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    plant_diary = relationship("PlantDiary", back_populates="user")

class PlantDiary(Base):
    __tablename__ = "plant_diary"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user.user_id")) 
    crop_id = Column(Integer, ForeignKey("crop.crop_id"))
    image_url = Column(String(2048))
    disease_id = Column(Integer, ForeignKey("disease.disease_id"), nullable=True)
    pest_id = Column(Integer, ForeignKey("pests.pest_id"), nullable=True)
    confidence = Column(Float)
    user_note = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    user = relationship("User", back_populates="plant_diary")
    crop = relationship("Crop")
    disease = relationship("Disease")
    pest = relationship("Pest")
