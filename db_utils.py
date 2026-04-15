import pymysql 
import os
from dotenv import load_dotenv

import models

load_dotenv()

def get_db_connection():
    return pymysql.connect(
        user = os.getenv("DB_USER"),
        password = os.getenv("DB_PASSWORD"),
        host = os.getenv("DB_HOST"),
        database = os.getenv("DB_NAME"),
        cursorclass=pymysql.cursors.DictCursor
    )

async def get_or_complete_knowledge(table_name, name_val, db):
    from test_gemini import client
    """
    智慧化知識庫管理：
    - 支援 crop: 僅取得或新增 ID。
    - 支援 disease/pest: 取得或新增 ID，且若為新增則由 AI 補完百科資訊。
    """
    # 1. 根據 table_name 映射對應的 SQLAlchemy 模型與欄位
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
        print(f"錯誤的 table_name: {table_name}")
        return None

    # 2. 執行查詢
    entry = db.query(model).filter(name_attr == name_val).first()

    # 3. 如果找到了，直接回傳
    if entry:
        result = {"id": getattr(entry, id_attr)}
        # 只有疾病和害蟲需要回傳建議與治療
        if table_name in ["disease", "pest"]:
            result["suggestion"] = getattr(entry, "description", "暫無描述")
            result["treatment"] = getattr(entry, "treatment", "暫無建議")
        return result

    # 4. 如果沒找到且是 Crop：直接新增後回傳
    if table_name == "crop":
        print(f"--- 知識庫查無作物『{name_val}』，自動新增 ---")
        new_crop = models.Crop(crop_name=name_val)
        db.add(new_crop)
        db.commit()
        db.refresh(new_crop)
        return {"id": new_crop.crop_id}

    # 5. 如果沒找到且是 Disease/Pest：啟動 AI 自動補完百科
    print(f"--- 知識庫查無『{name_val}』，啟動 AI 自動補完 ---")
    prompt = f"你是農業專家，請針對『{name_val}』提供百科資訊。格式：\n現象描述：(30字內)\n處理建議：(50字內)"
    
    try:
        response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
        ai_text = response.text
        # 解析 AI 回傳文字
        new_desc = ai_text.split("現象描述：")[1].split("處理建議：")[0].strip() if "現象描述：" in ai_text else "暫無描述"
        new_treat = ai_text.split("處理建議：")[1].strip() if "處理建議：" in ai_text else "暫無建議"
    except Exception as e:
        print(f"Gemini 生成失敗: {e}")
        new_desc, new_treat = "暫無描述", "暫無建議"

    # 6. 存入資料庫
    new_knowledge = model()
    # 使用 setattr 動態設定名稱欄位 (例如 disease_name = name_val)
    setattr(new_knowledge, name_attr.key, name_val)
    new_knowledge.description = new_desc
    new_knowledge.treatment = new_treat
    
    db.add(new_knowledge)
    db.commit()
    db.refresh(new_knowledge)

    return {
        "id": getattr(new_knowledge, id_attr),
        "suggestion": new_desc,
        "treatment": new_treat
    }

def get_crop_id_by_name(crop_name):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            sql = "SELECT crop_id FROM crop WHERE crop_name = %s"
            cursor.execute(sql, (crop_name,))
            result =  cursor.fetchone()
            if result:
                return result["crop_id"]
            else:
                print(f"⚠️ 警告：crop 表找不到名為 '{crop_name}' 的植物")
                return None
    finally:
        conn.close()