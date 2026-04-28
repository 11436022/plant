from app.db import models
from fastapi import HTTPException

async def get_or_complete_knowledge(table_name, name_val, db):
    """查詢知識表，若不存在則補齊資料。"""

    from app.services.ai import client,check_if_real_crop

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
                detail=f"'{name_val}' 不像是一個有效的植物名稱，請重新輸入。"
            )
        new_crop = models.Crop(crop_name=name_val)
        db.add(new_crop)
        db.commit()
        db.refresh(new_crop)
        return {"id": new_crop.crop_id}

    prompt = (
        f"Provide a short description and treatment for {name_val}. "
        "Format the response as:\n"
        "Description: ...\n"
        "Treatment: ..."
    )

    try:
        response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
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
