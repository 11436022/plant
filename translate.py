import time

import models
from database import SessionLocal
from googletrans import Translator


def translate_crops():
    """將尚未翻譯的作物中文名稱批次翻成英文。"""

    db = SessionLocal()
    translator = Translator()
    crops = db.query(models.Crop).filter(models.Crop.crop_name_en == None).all()

    # 逐筆翻譯，並加上少量延遲避免請求過快。
    for crop in crops:
        try:
            time.sleep(0.5)
            result = translator.translate(text=crop.crop_name, src="zh-tw", dest="en")

            crop.crop_name_en = result.text.title()
            print(f"ID {crop.crop_id}: {crop.crop_name} -> {crop.crop_name_en}")

            # 每 10 筆提交一次，避免交易過大。
            if crop.crop_id % 10 == 0:
                db.commit()
        except Exception as e:
            print(f"Error translating {crop.crop_name}: {e}")
            continue

    db.commit()
    db.close()
    print("Translation completed.")


if __name__ == "__main__":
    translate_crops()
