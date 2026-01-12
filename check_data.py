from database import SessionLocal
from models import Crop, Disease, DiseaseHarmPart

db = SessionLocal()

# 檢查作物
crops = db.query(Crop).all()
print("作物：")
for c in crops:
    print(f"  {c.crop_id}: {c.crop_name}")

diseases = db.query(Disease).all()
print("疾病：")
for d in diseases:
    print(f"  {d.disease_id}: {d.disease_name} ({d.crop.crop_name})")

harm_parts = db.query(DiseaseHarmPart).all()
print("危害部位：")
for h in harm_parts:
    print(f"  {h.harm_id}: {h.harm_part} - {h.harm_description}")

db.close()