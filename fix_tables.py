from database import engine
from sqlalchemy import text

with engine.connect() as conn:
    try:
        conn.execute(text("DROP TABLE IF EXISTS disease_harm_parts;"))
        conn.commit()
        print("disease_harm_parts 表已刪除")
    except Exception as e:
        print(f"刪除表時出錯: {e}")

    # 重新創建
    from models import Base
    Base.metadata.create_all(bind=engine)
    print("表已重新創建")