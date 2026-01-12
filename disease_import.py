import requests
import re
from database import SessionLocal
from models import Crop, Disease, DiseaseHarmPart

def fetch_api_116():
    # 使用你測試成功的正確網址
    url = "https://data.moa.gov.tw/Service/OpenData/FromM/blightdialoguedata.aspx?UnitId=116"
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"API 抓取失敗: {e}")
        return []

def import_116_data():
    db = SessionLocal()
    data = fetch_api_116()
    
    if not data:
        print("沒有抓取到資料。")
        return

    # 危害部位關鍵字
    PART_KEYWORDS = {"葉": "LEAF", "果": "FRUIT", "根": "ROOT", "莖": "STEM", "花": "FLOWER"}
    count = 0

    for item in data:
        # 1. 處理作物名稱 (去除空白)
        raw_crop_name = item.get("品名", "").strip()
        c_name = raw_crop_name.split()[0] if raw_crop_name else ""

        # 2. 處理疾病名稱 (從「解答」中提取，例如：黑斑病)
        # 這裡用簡單的正規表達式找「某某病」或「某某蛾」
        solution = item.get("解答", "")
        disease_match = re.search(r'([\w]+(?:病|蛾|蟬|蟎|蟲|障礙|症))', solution)
        if disease_match:
            d_name = disease_match.group(1)
        else:
        # 2. 如果找不到標準名，就取「解答」的前 10 個字作為名稱 (例如：研判為植物生理障礙)
            d_name = solution[:15] if solution else "未知狀況"
        
        # 判斷疾病類型
        if any(kw in d_name for kw in ["障礙", "缺", "水", "乾", "熱", "日灼", "肥害"]):
            d_type = "環境生理"
        # 接著根據解答內容判定生物性類別
        elif "真菌" in solution or "黴菌" in solution:
            d_type = "真菌"
        elif "細菌" in solution:
            d_type = "細菌"
        elif "病毒" in solution:
            d_type = "病毒"
        elif any(kw in solution for kw in ["蟲", "蛾", "蟬", "蟎", "幼蟲"]):
            d_type = "害蟲"
        else:
            d_type = "其他"
        
        # 取得農民提出的問題（病徵描述）
        description = item.get("問題", "")

        # 如果連作物名都沒有，或者沒識別出病名，就跳過這一筆不處理
        if not c_name or d_name == "未知病害":
            continue

        # 3. 查找作物 (確保你之前跑過 crud.py)
        crop = db.query(Crop).filter(Crop.crop_name.like(f"%{c_name}%")).first()
        if not crop:
            # 如果找不到，就現場建立一個作物
            crop = Crop(crop_name=c_name)
            db.add(crop)
            try:
                db.flush()
            except Exception as e:
                print(f"建立作物失敗: {c_name}, 錯誤: {e}")
                continue

        # 4. 建立疾病
        disease = db.query(Disease).filter_by(crop_id=crop.crop_id, disease_name=d_name).first()
        if not disease:
            print(f"嘗試建立疾病: {d_name} for {c_name}, crop_id: {crop.crop_id}")
            disease = Disease(
                crop_id=crop.crop_id,
                disease_name=d_name,
                description=description,
                disease_type=d_type
            )
            db.add(disease)
            try:
                db.flush()
                count += 1
                print(f"成功建立疾病: {d_name}")
            except Exception as e:
                print(f"建立疾病失敗: {d_name} for {c_name}, 錯誤: {e}")
                db.rollback()
                continue

        # 5. 解析危害部位 (從「問題」描述中判定)
        for kw, enum_val in PART_KEYWORDS.items():
            if kw in description:
                exists_part = db.query(DiseaseHarmPart).filter_by(
                    disease_id=disease.disease_id,
                    harm_part=enum_val
                ).first()
                if not exists_part:
                    db.add(DiseaseHarmPart(
                        disease_id=disease.disease_id,
                        harm_part=enum_val,
                        harm_description=f"自動判定: {kw}"
                    ))

    try:
        db.commit()
        print(f"--- 匯入完成，成功新增 {count} 筆疾病資料 ---")
    except Exception as e:
        db.rollback()
        print(f"寫入出錯: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    import_116_data()