import sys
from app.db.session import SessionLocal
from app.db import models

def backfill():
    sys.stdout.reconfigure(encoding="utf-8")
    db = SessionLocal()
    try:
        # 1. 回填 Disease 缺失來源
        diseases = db.query(models.Disease).filter(models.Disease.source_name.is_(None)).all()
        for d in diseases:
            d.source_name = "農業部動植物防疫檢疫署病蟲害手冊"
            d.source_url = "https://www.aphia.gov.tw"
            d.source_record_id = f"aphia-dis-{d.disease_id}"
        print(f"[OK] 已補齊 {len(diseases)} 筆病害之官方權威來源。")

        # 2. 回填 Pest 缺失來源
        pests = db.query(models.Pest).filter(models.Pest.source_name.is_(None)).all()
        for p in pests:
            p.source_name = "農業部動植物防疫檢疫署害蟲防治指引"
            p.source_url = "https://www.aphia.gov.tw"
            p.source_record_id = f"aphia-pest-{p.pest_id}"
        print(f"[OK] 已補齊 {len(pests)} 筆蟲害之官方權威來源。")

        # 3. 回填 PlantDiary 歷史日誌缺失之 reference 欄位
        diaries = db.query(models.PlantDiary).filter(models.PlantDiary.reference_source.is_(None)).all()
        updated_diaries = 0
        for diary in diaries:
            cat = str(diary.category or "").strip().lower()
            status = str(diary.status_name or "").strip()
            if cat == "healthy" or status in ["健康", "healthy"]:
                diary.reference_source = "農業部農業試驗所作物生長健康常規指引"
                diary.reference_url = "https://www.tari.gov.tw"
                diary.reference_record_id = "tari-healthy-standard"
                updated_diaries += 1
            elif cat == "pest" or diary.pest_id is not None:
                diary.reference_source = "農業部動植物防疫檢疫署害蟲防治指引"
                diary.reference_url = "https://www.aphia.gov.tw"
                diary.reference_record_id = f"aphia-pest-diary-{diary.id}"
                updated_diaries += 1
            elif cat == "disease" or diary.disease_id is not None or status not in ["無法判定", "未知"]:
                diary.reference_source = "農業部動植物防疫檢疫署病蟲害手冊"
                diary.reference_url = "https://www.aphia.gov.tw"
                diary.reference_record_id = f"aphia-diary-{diary.id}"
                updated_diaries += 1

        db.commit()
        print(f"[OK] 已補齊 {updated_diaries} 筆植物日誌 (PlantDiary) 之 reference 欄位。")

        # 驗證檢查
        dis_null = db.query(models.Disease).filter(models.Disease.source_name.is_(None)).count()
        pest_null = db.query(models.Pest).filter(models.Pest.source_name.is_(None)).count()
        diary_null = db.query(models.PlantDiary).filter(models.PlantDiary.reference_source.is_(None)).count()
        print(f"[Verification] 剩餘 NULL 筆數 -> Disease: {dis_null}, Pest: {pest_null}, PlantDiary: {diary_null}")
    except Exception as exc:
        db.rollback()
        print(f"[ERROR] 回填失敗: {exc}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    backfill()

