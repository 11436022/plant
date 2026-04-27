"""
根目錄入口點：純粹負責啟動 uvicorn。
所有的 FastAPI 設定（含 mount）都應留在 app/main.py 內。
"""
from app.core.config import API_HOST, API_PORT
from app.main import app  # 這裡會自動觸發 app/main.py 裡的設定

if __name__ == "__main__":
    import uvicorn
    # 啟動從 app.main 匯入的 app 實例
    uvicorn.run(app, host=API_HOST, port=API_PORT)