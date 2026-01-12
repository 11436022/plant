from database import engine
from sqlalchemy import text

with engine.connect() as conn:
    result = conn.execute(text("SHOW TABLES;"))
    tables = result.fetchall()
    print("現有表：", tables)