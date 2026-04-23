from database import SessionLocal
from models import Crop
from api_fetch import fetch_crop_data


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
