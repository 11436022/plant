# 1. 使用跟你一模一樣的基礎鏡像
FROM pytorch/pytorch:2.5.1-cuda12.1-cudnn9-devel

# 2. 設定容器內的工作目錄
WORKDIR /app

# 3. 安裝系統必要的工具 (如果有用到 OpenCV 或是其他基礎庫)
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# 4. 直接安裝核心套件 (不使用 requirements.txt 避免版本鎖死)
RUN pip install --no-cache-dir \
    fastapi \
    uvicorn \
    pymysql \
    python-dotenv \
    Pillow \
    google-genai \
    google-api-core \
    google-auth \
    python-multipart \
    cryptography \
    bcrypt==4.0.1 \
    pydantic[email] \
    passlib[bcrypt] \
    PyJWT

COPY . .
# 5. 告訴容器啟動時要跑什麼
CMD ["python3", "main.py"]