from database import SessionLocal
from models import Crop
from api_fetch import fetch_crop_data

def save_main_crops():
    db = SessionLocal()
    data = fetch_crop_data()
    saved = set()

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
    print(f"已存入 {len(saved)} 種主要作物")

if __name__ == "__main__":
    save_main_crops()    