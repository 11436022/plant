# 使用官方的 Python 輕量級映像檔作為基礎
FROM python:3.11-slim

# 設定工作目錄
WORKDIR /app

# 安裝系統必要的工具，並在結束後清理，以保持映像檔小巧
RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# 建立一個虛擬環境，這是一個好的實踐
RUN python3 -m venv /opt/venv

# 將虛擬環境的路徑加入到 PATH，這樣後續的指令會優先使用 venv 中的 python 和 pip
ENV PATH="/opt/venv/bin:$PATH"

# 複製 requirements.txt 並安裝依賴
# 這樣做可以利用 Docker 的層快取機制，只有當 requirements.txt 變動時才會重新安裝
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 複製整個專案到工作目錄
COPY . .

# 建立一個非 root 的使用者來運行應用程式，增加安全性
RUN useradd --create-home appuser
# 將工作目錄的擁有權交給新使用者
RUN chown -R appuser:appuser /app
# 切換到新使用者
USER appuser

# 設定容器啟動時執行的指令
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]