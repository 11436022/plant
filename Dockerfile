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
    ca-certificates \
    libgomp1 \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

ENV TZ=Asia/Taipei
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# 建立虛擬環境以隔離依賴
RUN python3 -m venv /opt/venv

# 優先複製 requirements.txt 並安裝依賴，利用 Docker 層快取機制
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# 複製整個專案到工作目錄
COPY . .

# 若目錄下無模型權重檔，自動由官方 GitHub Release 下載 ConvNeXt 權重
RUN if [ ! -f convnext_plant_best.pth ]; then \
        echo "Downloading convnext_plant_best.pth from GitHub Releases..." && \
        curl -L -o convnext_plant_best.pth https://github.com/11436022/plant/releases/download/v1.0-weights/convnext_plant_best.pth; \
    fi
# 預先建立靜態資源與上傳檔案目錄，並將預載種子與圖片庫備份至 /app/static_seed
RUN mkdir -p /app/static/uploads /app/static/feedback_uploads /app/static/tmp \
    && cp -r /app/static /app/static_seed

# 宣告監聽的連接埠
EXPOSE 8000

# 容器健康檢查設定
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/ || exit 1

# 設定容器啟動指令 (啟動前確保 Volume 具備必要子目錄，並將種子圖片與快取同步還原至 Volume，且強制更新最新 APK)
CMD ["sh", "-c", "mkdir -p /app/static/uploads /app/static/feedback_uploads /app/static/tmp && (cp -rn /app/static_seed/* /app/static/ 2>/dev/null || true) && ([ -f /app/static_seed/uploads/plantdoctor.apk ] && cp -f /app/static_seed/uploads/plantdoctor.apk /app/static/uploads/plantdoctor.apk || true) && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
