import os
import sys
from dotenv import load_dotenv

# 1. 確保路徑正確，並讀取 .env 檔案
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)
load_dotenv(os.path.join(current_dir, ".env"))

try:
    # 2. 現在才匯入 app 的東西（這時候環境變數已經讀到了）
    from app.database import engine, Base
    import app.models 
    
    print(f"正在連接資料庫：{os.getenv('DB_NAME')}...")
    Base.metadata.create_all(bind=engine)
    print("✅ 資料表建立成功！")
    
except Exception as e:
    print(f"❌ 發生錯誤：{e}")