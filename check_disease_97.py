from database import SessionLocal
from models import Disease

db = SessionLocal()
diseases = db.query(Disease).filter(Disease.crop_id == 97).all()
print(f"crop_id 97 的疾病:")
for d in diseases:
    print(f"  {d.disease_name}")
db.close()