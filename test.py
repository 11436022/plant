from database import SessionLocal
from models import Crop,Disease

db = SessionLocal()

try:
    target_crop = db.query(Crop).filter(Crop.crop_name == "萵苣").first()
    if target_crop:
        print(print(f"找到作物：{target_crop.crop_name}，ID 為：{target_crop.crop_id}"))
        new_disease = Disease(
            crop_id = target_crop.crop_id,
            disease_name = "萵苣霜黴病",
            description = "病徵為葉片正面出現淡黃色不規則病斑，潮濕時背面有白色黴層。"
        )

        db.add(new_disease)
        db.commit()
        print(f"✅ 成功將「{new_disease.disease_name}」新增至「{target_crop.crop_name}」下！")
    else:
        print("❌ 找不到名為 '萵苣' 的作物，請先確認資料庫中是否有該筆資料。")
except Exception as e:
    db.rollback()
    print(f"❌ 發生錯誤：{e}")
finally:
    db.close()