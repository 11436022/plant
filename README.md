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
DB_HOST=localhost
DB_NAME=plant_db

### 3. 建立本地資料庫
請開啟 MySQL，手動執行以下指令建立資料庫：
CREATE DATABASE plant_db;

### 📂 檔案結構說明
database.py: 資料庫連線配置中心，使用 dotenv 讀取環境變數。
models.py: 定義資料庫表格結構 (ORM)。
api_fetch.py : 從農業 API 抓取資料並回傳 JSON把資料抓下來存成檔案
crud.py: 負責資料庫操作

1. 請先執行 python api_fetch.py 獲取最新農業資料。
2. 再執行 python crud.py 將抓取到的資料同步至資料庫。