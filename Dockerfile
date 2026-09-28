# 使用官方 Python 3.11 輕量級映像檔作為基礎
FROM python:3.11-slim

# 設定即時輸出日誌與避免生成 pyc 快取檔
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH"

# 設定工作目錄
WORKDIR /app

# 安裝系統必要的工具：
# - curl: 供容器健康檢查（HEALTHCHECK）使用
# - libgomp1: FAISS 向量檢索函式庫所必需之 OpenMP 支援
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# 建立虛擬環境以隔離依賴
RUN python3 -m venv /opt/venv

# 優先複製 requirements.txt 並安裝依賴，利用 Docker 層快取機制
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# 複製整個專案到工作目錄
COPY . .

# 預先建立靜態資源與上傳檔案目錄，並建立非 root 使用者以強化容器安全性
RUN mkdir -p /app/static/uploads /app/static/feedback_uploads \
    && useradd --create-home appuser \
    && chown -R appuser:appuser /app

# 切換到非 root 使用者運行
USER appuser

# 宣告監聽的連接埠
EXPOSE 8000

# 容器健康檢查設定
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/ || exit 1

# 設定容器啟動指令
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]