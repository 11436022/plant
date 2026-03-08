from googletrans import Translator
from sqlalchemy.orm import Session
from database import SessionLocal, engine
import models
import time


def translate_crops():
    db = SessionLocal()
    translator = Translator()
    crops = db.query(models.Crop).filter(models.Crop.crop_name_en == None).all()
    for crop in crops:
        try:
            time.sleep(0.5)
            result = translator.translate(text=crop.crop_name, src="zh-tw", dest="en")

            crop.crop_name_en = result.text.title()
            print(f"ID {crop.crop_id}: {crop.crop_name} -> {crop.crop_name_en}")

            if crop.crop_id % 10 ==0:
                db.commit()
        except Exception as e:
            print(f"Error translating {crop.crop_name}: {e}")
            continue
    db.commit()
    db.close()
    print("Translation completed.")
if __name__ == "__main__":
    translate_crops()

