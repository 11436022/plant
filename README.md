# 植栽與病害管理系統 (Plant Backend)

這是一個基於 Python 與 MySQL 開發的後端專案，主要功能是管理作物資料、抓取病害資訊並儲存於資料庫中。

## 🛠 專案功能
* **作物資料管理**：收錄超過 800 種作物資訊。
* **病害診斷紀錄**：整合作物對應的病害描述、類型及受害部位。
* **資料庫同步**：提供完整的 SQL 備份檔，方便快速部署。

## 📁 檔案說明
* `api_fetch`: url為農業資料開發平台。
* `database.py`: MySQL 資料庫連線設定。
* `models.py`: 定義資料庫資料表結構 。
Crop:農作物 disease:疾病 disease_harm_part:疾病部位 pests:害蟲
* `plant_db_setup_fixed.sql`: 資料庫還原檔案（包含結構與 500+ 筆資料）。
### 1. 複製專案
```bash
git clone [https://github.com/11436022/plant.git](https://github.com/11436022/plant.git)
cd plant_backend