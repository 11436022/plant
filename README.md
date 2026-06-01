## 精準農業：植物病害診斷系統 - 後端設定指南
本專案使用 Python (SQLAlchemy) 與 MySQL 進行開發。為了確保所有組員的開發環境一致，請按照以下步驟進行設定。

### 1. 複製專案與安裝環境
首先，請將專案從 GitHub 下載到你的電腦，並安裝必要的 Python 套件：

# 下載專案 
git clone <https://github.com/11436022/plant.git>


# 安裝必要套件
pip install -r requirements.txt

### 2. 設定個人環境變數 (.env)
為了保護每個人的資料庫密碼，我們不將密碼寫在程式碼中。請在專案根目錄手動建立一個 .env 檔案，並填入你自己的資料庫資訊：

# .env 內容範例
DB_USER=你的MySQL帳號 (例如 root)
DB_PASSWORD=你的MySQL密碼
DB_HOST=host.docker.internal
DB_HOST=127.0.0.1 
DB_NAME=plant_db
# local.properties.example
要把WIFI_HOST 改成你自己的IP位址
### 3. 建立本地資料庫
請開啟 MySQL，手動執行以下指令建立資料庫：
init_db.sql可以直接複製到mysql去建立
### (2026/4/28更新)現在請直接跑以下步驟(打開terminal)：
git pull origin main
python -m alembic upgrade head
python seed.py

### 📂 檔案結構說明
以下是專案主要的檔案與目錄結構：

```
.
├── alembic/              # 資料庫遷移腳本 (Alembic)
├── app/                  # 主要後端應用程式目錄
│   ├── core/             # 核心設定
│   │   └── config.py     # 應用程式設定檔，會讀取 .env 的變數
│   ├── db/               # 資料庫相關模組
│   │   ├── models.py     # SQLAlchemy 的 ORM 模型定義
│   │   └── session.py    # 資料庫連線 Session 管理
│   ├── routers/          # API 路由定義 (FastAPI Routers)
│   ├── schemas/          # Pydantic 資料驗證模型
│   ├── services/         # 核心商業邏輯服務 (如 AI, 認證, Email)
│   ├── crud.py           # 負責基本資料庫的 CRUD 操作
│   └── main.py           # FastAPI 應用程式啟動進入點
├── frontend/             # 前端 Android 應用程式
│   └── plantdoctor/
│       ├── local.properties          # Android 的本地環境設定 (如 SDK 路徑, WIFI_HOST)，不受版本控制
│       └── local.properties.example  # local.properties 的設定範本
├── static/               # 靜態檔案
│   └── uploads/          # 使用者上傳的檔案存放處
├── .env                  # 本地環境變數設定 (如資料庫密碼)，不受版本控制
├── .env.example          # .env 的設定範本
├── alembic.ini           # Alembic 的設定檔
├── docker-compose.yml    # Docker Compose 設定檔
├── dockerfile            # 後端應用程式的 Dockerfile
├── requirements.txt      # Python 套件依賴列表
└── seed.py               # 資料庫初始資料填充腳本
```

# 如果有更改資料庫要去alembic,才能同步


# docker
### 一樣要先建好 資料庫 還有下載docker desktop
### 要改成 DB_HOST=host.docker.internal
## 1. 先建立映像檔 (只需要做一次)
docker build -t plant-app-final .

## 2. 啟動容器 (每次要跑程式時執行這行)
docker run --gpus all -it -p 8000:8000 -v ${PWD}:/app plant-app-final bash -c "cd /app && python3 main.py"

## 如果網頁跑不出來網址改成  http://localhost:8000/docs

### Alembic (資料庫同步)
## Alembic 用法
pip install alembic pymysql python-dotenv
python -m alembic current
python -m alembic upgrade head

## Alembic 抓法
git pull origin main
python -m alembic upgrade head