from app.db import models
from fastapi import HTTPException

async def get_or_complete_knowledge(table_name, name_val, db):
    """查詢知識表，若不存在則補齊資料。"""

    from app.services.ai import client, check_if_real_crop, call_gemini_with_fallback

    if table_name == "crop":
        model = models.Crop
        name_attr = models.Crop.crop_name
        id_attr = "crop_id"
    elif table_name == "disease":
        model = models.Disease
        name_attr = models.Disease.disease_name
        id_attr = "disease_id"
    elif table_name == "pest":
        model = models.Pest
        name_attr = models.Pest.pest_name
        id_attr = "pest_id"
    else:
        return None

    entry = db.query(model).filter(name_attr == name_val).first()
    if entry:
        result = {"id": getattr(entry, id_attr)}
        if table_name in {"disease", "pest"}:
            result["suggestion"] = getattr(entry, "description", "No suggestion available.")
            result["treatment"] = getattr(entry, "treatment", "No treatment available.")
        return result

    if table_name == "crop":
        is_valid = await check_if_real_crop(name_val)
        if not is_valid:
            # 如果不是植物，直接報錯，中斷流程
            raise HTTPException(
                status_code=400, 
                detail=f"\'{name_val}\' 不像是一個有效的植物名稱，請重新輸入。"
            )
        new_crop = models.Crop(crop_name=name_val)
        db.add(new_crop)
        db.commit()
        db.refresh(new_crop)
        return {"id": new_crop.crop_id}

    prompt = (
        f"Provide a short description and treatment for {name_val}. "
        "Format the response as:\\n"
        "Description: ...\\n"
        "Treatment: ..."
    )

    try:
        response = call_gemini_with_fallback(contents=prompt)
        ai_text = response.text or ""
    except Exception:
        ai_text = ""

    description = "No suggestion available."
    treatment = "No treatment available."
    for line in ai_text.splitlines():
        lower = line.lower()
        if lower.startswith("description:"):
            description = line.split(":", 1)[1].strip() or description
        if lower.startswith("treatment:"):
            treatment = line.split(":", 1)[1].strip() or treatment

    new_knowledge = model()
    setattr(new_knowledge, name_attr.key, name_val)
    new_knowledge.description = description
    new_knowledge.treatment = treatment

    db.add(new_knowledge)
    db.commit()
    db.refresh(new_knowledge)

    return {
        "id": getattr(new_knowledge, id_attr),
        "suggestion": description,
        "treatment": treatment,
    }

def get_crop_id_by_name(crop_name):
    """依作物名稱查詢主鍵。"""

    from app.db.session import get_db_connection

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT crop_id FROM crop WHERE crop_name = %s", (crop_name,))
            result = cursor.fetchone()
            if result:
                return result["crop_id"]
            return None
    finally:
        conn.close()

def ensure_crop_exists_in_db(crop_name: str, conn=None, db=None) -> int | None:
    """
    【主動學習作物自動登錄】
    當專家在後台校正、標註或視覺記憶庫收錄新植物時，
    自動檢測並將新作物登錄至官方 crop 資料庫，確保前端 App 下拉選單即時可選。
    支援 SQLAlchemy Session (db) 與原生 PyMySQL 連線 (conn)。
    """
    from app.services.visual_memory import is_valid_crop_name
    if not is_valid_crop_name(crop_name):
        return None

    clean_name = crop_name.strip()

    # 1. 優先使用傳入的 SQLAlchemy db Session
    if db is not None:
        from app.db import models
        entry = db.query(models.Crop).filter(models.Crop.crop_name == clean_name).first()
        if entry:
            return entry.crop_id
        try:
            new_crop = models.Crop(crop_name=clean_name)
            db.add(new_crop)
            db.commit()
            db.refresh(new_crop)
            print(f"[ActiveLearning] 🌟 發現新植物標籤，已自動登錄至作物字典：【{clean_name}】(crop_id: {new_crop.crop_id})")
            return new_crop.crop_id
        except Exception:
            db.rollback()
            fallback = db.query(models.Crop).filter(models.Crop.crop_name == clean_name).first()
            return fallback.crop_id if fallback else None

    # 2. 原生 PyMySQL 連線模式
    from app.db.session import get_db_connection

    should_close = False
    if conn is None:
        conn = get_db_connection()
        should_close = True

    try:
        import pymysql
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute("SELECT crop_id FROM crop WHERE crop_name = %s", (clean_name,))
            row = cursor.fetchone()
            if row:
                return row["crop_id"]

            try:
                cursor.execute("INSERT INTO crop (crop_name) VALUES (%s)", (clean_name,))
                conn.commit()
                new_id = cursor.lastrowid
                print(f"[ActiveLearning] 🌟 發現新植物標籤，已自動登錄至作物字典：【{clean_name}】(crop_id: {new_id})")
                return new_id
            except Exception as e:
                conn.rollback()
                cursor.execute("SELECT crop_id FROM crop WHERE crop_name = %s", (clean_name,))
                fallback_row = cursor.fetchone()
                return fallback_row["crop_id"] if fallback_row else None
    finally:
        if should_close:
            conn.close()


def ensure_disease_exists_in_db(crop_id: int, disease_name: str, conn=None, db=None) -> int | None:
    """
    【主動學習病害自動登錄】
    當專家校正或發現新病徵時，自動登錄至官方 disease 資料庫，維持資料庫關聯完整性。
    支援 SQLAlchemy Session (db) 與原生 PyMySQL 連線 (conn)。
    """
    from app.services.visual_memory import is_valid_disease_status
    if not is_valid_disease_status(disease_name) or disease_name in ["健康", "未知"]:
        return None

    clean_disease = disease_name.strip()

    # 1. 優先使用傳入的 SQLAlchemy db Session
    if db is not None:
        from app.db import models
        entry = db.query(models.Disease).filter(
            models.Disease.crop_id == crop_id, models.Disease.disease_name == clean_disease
        ).first()
        if entry:
            return entry.disease_id
        try:
            desc = f"{clean_disease}之典型病徵（由農業專家主動學習覆核登錄）。"
            treat = "1. 請依照專家建議之對應處方進行植株照護。\n2. 維持良好通風與田間水分管理。"
            new_dis = models.Disease(
                crop_id=crop_id,
                disease_name=clean_disease,
                description=desc,
                treatment=treat,
                source_name="專家主動學習覆核新定名"
            )
            db.add(new_dis)
            db.commit()
            db.refresh(new_dis)
            print(f"[ActiveLearning] 🌟 發現新病害標籤，已自動登錄至官方病害庫：【{clean_disease}】(disease_id: {new_dis.disease_id})")
            return new_dis.disease_id
        except Exception:
            db.rollback()
            fallback = db.query(models.Disease).filter(
                models.Disease.crop_id == crop_id, models.Disease.disease_name == clean_disease
            ).first()
            return fallback.disease_id if fallback else None

    # 2. 原生 PyMySQL 連線模式
    from app.db.session import get_db_connection

    should_close = False
    if conn is None:
        conn = get_db_connection()
        should_close = True

    try:
        import pymysql
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute(
                "SELECT disease_id FROM disease WHERE crop_id = %s AND disease_name = %s",
                (crop_id, clean_disease)
            )
            row = cursor.fetchone()
            if row:
                return row["disease_id"]

            try:
                sql_insert = """
                    INSERT INTO disease (crop_id, disease_name, description, treatment, source_name)
                    VALUES (%s, %s, %s, %s, '專家主動學習覆核新定名')
                """
                desc = f"{clean_disease}之典型病徵（由農業專家主動學習覆核登錄）。"
                treat = "1. 請依照專家建議之對應處方進行植株照護。\n2. 維持良好通風與田間水分管理。"
                cursor.execute(sql_insert, (crop_id, clean_disease, desc, treat))
                conn.commit()
                new_id = cursor.lastrowid
                print(f"[ActiveLearning] 🌟 發現新病害標籤，已自動登錄至官方病害庫：【{clean_disease}】(disease_id: {new_id})")
                return new_id
            except Exception as e:
                conn.rollback()
                cursor.execute(
                    "SELECT disease_id FROM disease WHERE crop_id = %s AND disease_name = %s",
                    (crop_id, clean_disease)
                )
                fallback_row = cursor.fetchone()
                return fallback_row["disease_id"] if fallback_row else None
    finally:
        if should_close:
            conn.close()
