from sqlalchemy import Column, Integer, String, Text, ForeignKey, Enum
from sqlalchemy.orm import relationship
from database import Base

class Crop(Base):
    __tablename__ = "crop"
    crop_id = Column(Integer, primary_key=True, index=True)
    crop_name = Column(String(100), unique=True, nullable=False)
    diseases = relationship("Disease", back_populates="crop")
    pests = relationship("Pest", back_populates="crop")

class Disease(Base):
    __tablename__ = "disease"
    disease_id = Column(Integer, primary_key=True, index=True)
    crop_id = Column(Integer, ForeignKey("crop.crop_id"))
    disease_name = Column(String(100), nullable=False)
    disease_type = Column(String(50))
    description = Column(Text)
    crop = relationship("Crop", back_populates="diseases")
    harm_parts = relationship("DiseaseHarmPart", back_populates="disease")

class DiseaseHarmPart(Base):
    __tablename__ = "disease_harm_part"
    harm_id = Column(Integer, primary_key=True, index=True)
    disease_id = Column(Integer, ForeignKey("disease.disease_id"))
    harm_part = Column(Enum('root','stem','leaf','flower','fruit','plant',name="harm_part_enum"))
    harm_description = Column(Text)
    disease = relationship("Disease", back_populates="harm_parts")   

class Pest(Base):
    __tablename__ = "pests"
    pest_id = Column(Integer, primary_key=True, index=True)
    crop_id = Column(Integer, ForeignKey("crop.crop_id"))
    pest_name = Column(String(100), nullable=False)
    affected_part = Column(Enum('root','stem','leaf','flower','fruit','plant',name="affected_part_enum"))
    description = Column(Text)
    crop = relationship("Crop", back_populates="pests")    
