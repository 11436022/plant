import json
from sqlalchemy.orm import Session
from database import SessionLocal, engine
import models
from app.db.models import Base

def seed_data():
    # 1. 確保資料表結構存在 (取代 init_db.sql)
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        with open('data.json', 'r', encoding='utf-8') as f:
            data = json.load(f)

        # 2. 同步植物 (Crops) - 最優先，因為後面需要它的 ID
        for c in data.get('crops', []):
            exists = db.query(models.Crop).filter_by(crop_name=c['crop_name']).first()
            if not exists:
                db.add(models.Crop(**c))
        db.commit() # 先提交植物，確保後面查得到 ID
        print("植物表同步完成")

        # 3. 同步疾病 (Diseases)
        for d in data.get('diseases', []):
            exists = db.query(models.Disease).filter_by(disease_name=d['disease_name']).first()
            if not exists:
                # 核心邏輯：用名稱去查資料庫目前的 crop_id
                target_crop = None
                if d.get('crop_name') and d['crop_name'] != "null":
                    target_crop = db.query(models.Crop).filter_by(crop_name=d['crop_name']).first()
                
                # 建立物件，排除 json 裡的 crop_name，改填入查到的 crop_id
                disease_data = d.copy()
                disease_data.pop('crop_name', None) # 移除暫時的名稱欄位
                if target_crop:
                    disease_data['crop_id'] = target_crop.crop_id
                
                db.add(models.Disease(**disease_data))
                print(f"已新增疾病: {d['disease_name']}")

        # 4. 同步害蟲 (Pests)
        for p in data.get('pests', []):
            exists = db.query(models.Pest).filter_by(pest_name=p['pest_name']).first()
            if not exists:
                target_crop = db.query(models.Crop).filter_by(crop_name=p['crop_name']).first()
                
                pest_data = p.copy()
                pest_data.pop('crop_name', None)
                if target_crop:
                    pest_data['crop_id'] = target_crop.crop_id
                
                db.add(models.Pest(**pest_data))
                print(f"已新增害蟲: {p['pest_name']}")

        db.commit()
        print("\n--- 所有資料初始化成功！ ---")

    except Exception as e:
        db.rollback()
        print(f"發生錯誤: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_data()