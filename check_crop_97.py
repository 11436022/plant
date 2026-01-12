from database import SessionLocal
from models import Crop

db = SessionLocal()
crop = db.query(Crop).filter(Crop.crop_id == 97).first()
if crop:
    print(f"crop_id 97: {crop.crop_name}")
else:
    print("crop_id 97 不存在")
db.close()