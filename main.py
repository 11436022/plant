"""
根目錄入口點：純粹負責啟動 uvicorn。
所有的 FastAPI 設定（含 mount）都應留在 app/main.py 內。
"""
# main.py

# 把原本那行改成這樣：
from app.core.config import settings

from app.main import app  # 這裡會自動觸發 app/main.py 裡的設定

if __name__ == "__main__":
    import uvicorn
    # 啟動從 app.main 匯入的 app 實例
    uvicorn.run(app, host=settings.API_HOST, port=settings.API_PORT)