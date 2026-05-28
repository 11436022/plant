# Stage 1: Builder
# 使用包含完整開發工具的映像檔來安裝依賴
FROM pytorch/pytorch:2.5.1-cuda12.1-cudnn9-devel as builder

WORKDIR /app

# 安裝系統必要的工具
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# 建立一個虛擬環境，並將安裝好的套件放在裡面
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# 先複製 requirements.txt 並安裝依賴，以便利用 Docker 快取
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 複製專案的其餘部分
COPY . .

# Stage 2: Runner
# 使用一個更輕量的基礎映像檔來運行應用程式
FROM pytorch/pytorch:2.5.1-cuda12.1-cudnn9-runtime

WORKDIR /app

# 建立一個非 root 使用者
RUN useradd --create-home appuser
USER appuser

# 從 builder 階段複製虛擬環境和應用程式碼
COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /app /app

# 設定環境變數，讓應用程式使用虛擬環境中的 Python
ENV PATH="/opt/venv/bin:$PATH"

# 告訴容器啟動時要跑什麼
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]