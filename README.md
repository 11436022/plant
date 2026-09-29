# Plant Doctor 植物病蟲害診斷系統

Plant Doctor 是一套以 Android App 與瀏覽器 Webcam 監控台為前端、FastAPI 為後端、MySQL 8.0 為資料庫，並結合 Google Gemini 多模態 AI、本地客製化模型、FAISS 檢索增強（RAG）官方知識庫與三方仲裁核心的智慧植物病蟲害診斷與監測系統。

---

## 系統核心特色與已完成功能

- **帳號安全與身分認證**
  - 使用者註冊、Gmail 信箱驗證啟用、安全密碼雜湊（bcrypt）
  - JWT Token 鑑權機制、忘記密碼與一性 Token 重設密碼網頁流程
- **多元前端與互動**
  - **Android 客戶端**：植物病斑拍照／相簿上傳、即時診斷確認、個人化歷史紀錄、備忘筆記編輯 (UC-08)、診斷紀錄刪除
  - **Webcam 實時監控控制台**：瀏覽器即時影像串流、定時影格擷取分析
- **AI 雙模型協同推論與三方仲裁核心 (Tripartite Arbitration Core)**
  - Google Gemini 多模態雲端大模型特徵辨識
  - 本地自訓客製化模型微觀分類
  - 信心度閾值檢核、作物／病蟲害名稱資料庫白名單校驗
  - 症狀與防治處置全面由官方驗證資料庫覆蓋，杜絕 AI 幻覺
- **診斷反饋與主動糾錯機制 (UC-13, UC-14)**
  - 使用者誤判反饋與標註圖片上傳
  - 管理後台回饋審核、真實標籤修正與重標註支援
- **Webcam 時序警報系統**
  - 連續多影格共識判定機制，防範單張畫面誤報
  - 支援聲音警示、瀏覽器通知與 SMTP 高危病害 Email 即時推播
  - 警報紀錄留存、後台確認與刪除管理
- **農業氣象與知識庫**
  - 整合中央氣象署 (CWA) 開放資料 API 提供即時農業氣象
  - 整合農業部官方病蟲害圖鑑與 FAISS 向量索引檢索增強 (RAG)
- **管理後台 (Admin Dashboard)**
  - 作物、病害、蟲害資料增刪查改
  - 使用者帳號與權限檢視、Webcam 警報記錄管理、診斷回饋審核

---

## 系統架構

```text
┌───────────────────────┐
│      Android App      │────────┐
└───────────────────────┘        │
                                 ├─── HTTP / JWT ───┐
┌───────────────────────┐        │                  │
│ Browser Webcam / Web  │────────┘                  ▼
└───────────────────────┘                  ┌──────────────────┐
                                           │ FastAPI 後端服務  │
                                           └────────┬─────────┘
                                                    │
                 ┌──────────────────┬───────────────┴───────────────┬──────────────────┐
                 ▼                  ▼                               ▼                  ▼
        ┌─────────────────┐ ┌───────────────┐              ┌─────────────────┐ ┌───────────────┐
        │  Google Gemini  │ │ 本地客製化模型  │              │ FAISS 向量知識庫 │ │  MySQL 8.0    │
        │  (雲端多模態)    │ │ (微觀分類器)   │              │ (RAG 檢索增強)  │ │ (持久化資料庫) │
        └─────────────────┘ └───────────────┘              └─────────────────┘ └───────────────┘
```

### 主要入口一覽

| 服務項目 | 存取網址 | 說明 |
| --- | --- | --- |
| **API 互動文件** | `http://localhost:8000/docs` | FastAPI Swagger UI 介面 |
| **API 替代文件** | `http://localhost:8000/redoc` | OpenAPI ReDoc 介面 |
| **Webcam 自動監控** | `http://localhost:8000/webcam` | 瀏覽器定時掃描與自動警報控制台 |
| **管理後台儀表板** | `http://localhost:8000/admin/` | 資料庫、警報紀錄與診斷回饋審核後台 |
| **重設密碼網頁** | `http://localhost:8000/reset-password-web` | 忘記密碼 Email 連結中介重設頁面 |
| **服務健康檢查** | `http://localhost:8000/` | 容器與伺服器運行狀態檢測 |

> [!NOTE]
> 瀏覽器規範只允許在 `localhost` 或 HTTPS 安全來源存取攝影機。若跨裝置/跨網段使用 Webcam 監控台，請設定 HTTPS 反向代理。

---

## 環境需求

- **Python**：3.11（或 3.10 以上）
- **資料庫**：MySQL 8.0
- **容器化支援**：Docker Engine 24+ 及 Docker Compose v2/v5+（符合 Compose Specification）
- **AI 服務金鑰**：Google Gemini API Key
- **瀏覽器**：Chrome、Edge 或支援 `getUserMedia` 的現代瀏覽器
- **行動裝置開發**：Android Studio（建置 Android App 時需要）

---

## 本地環境安裝與啟動

### 1. 複製專案與安裝依賴

```powershell
git clone https://github.com/11436022/plant.git
cd plant
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

### 2. 設定環境變數 (`.env`)

請編輯 `.env` 檔案，關鍵設定如下：

```dotenv
# AI 服務
GEMINI_API_KEY=your_gemini_api_key

# 資料庫連線
DB_HOST=127.0.0.1
DB_USER=plant
DB_PASSWORD=your_mysql_password
DB_NAME=plant_db

# JWT 認證密鑰
JWT_SECRET_KEY=replace_with_a_long_random_secret

# 外部網址與通訊
WIFI_HOST_IP=127.0.0.1
FRONTEND_BASE_URL=http://127.0.0.1:8000

# 郵件通知（選填，若無設定則畫面與資料庫仍正常運作，略過寄信）
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_account@gmail.com
SMTP_PASSWORD=your_app_password
SMTP_FROM_EMAIL=your_account@gmail.com

# 中央氣象署 API 金鑰（選填）
CWB_API_KEY=your_cwb_api_key
```

### 3. 下載 AI 模型權重（選填）

請至 [Releases 頁面](https://github.com/11436022/plant/releases) 下載 `convnext_plant_best.pth` 並放置於專案根目錄。
> 若未下載，系統會自動使用雲端 Gemini 診斷，不影響其他功能開發。

### 4. 資料庫遷移與初始化種子資料

```powershell
# 執行資料庫 Migration 至最新版本
python -m alembic upgrade head

# 匯入作物、病蟲害官方基本資料
python seed.py

# 建立 FAISS 向量知識庫索引
python build_knowledge_base.py
```

### 5. 啟動後端服務

```powershell
python main.py
```

---

## Docker 容器化部署（現行版本規範）

本專案支援現代 **Docker Compose Specification**（相容 `compose.yaml` 與 `docker-compose.yml`），並遵循安全與輕量化最佳實踐。

### 特性說明
- **現代 Compose 規範**：移除已過時的 `version` 宣告，避免過時語法警告。
- **跨平台主機網路互通**：內建 `extra_hosts: ["host.docker.internal:host-gateway"]`，容器可直接以 `DB_HOST=host.docker.internal` 連線至主機 MySQL。
- **資料持久化掛載**：同步掛載 `./static/uploads`（日記影像）與 `./static/feedback_uploads`（糾錯回饋影像）。
- **非 root 安全容器**：使用專用 `appuser` 運行，降低特權逃逸風險。
- **健康檢查與建置最佳化**：內建 `HEALTHCHECK` 定期檢驗；搭配 `.dockerignore` 排除前端、歷程庫與敏感金鑰，加速映像檔建置。

### Docker 常用指令

```powershell
# 驗證 Docker Compose 設定檔（零警告）
docker compose config

# 建置映像檔並於背景啟動容器
docker compose up -d --build

# 檢視後端即時日誌
docker compose logs -f web

# 停止並移除容器
docker compose down
```

> [!TIP]
> 容器化運行時若資料庫位於宿主機，請將 `.env` 中的 `DB_HOST` 設為 `host.docker.internal`。

---

## Webcam 自動監控與警報機制

1. 進入 `http://localhost:8000/webcam` 並登入既有帳號。
2. 授權選取攝影機設備，按下「開啟預覽」後點擊「啟動監控」。
3. 系統依設定週期擷取影格，並傳送至後端進行多影格共識判定。
4. 當相同且合規之病蟲害特徵連續命中達到預設門檻，立即觸發告警。
5. 警報會自動保存截圖、留存紀錄，並觸發音效、瀏覽器推播與 Email 通知。

預設警報控制門檻（可於 `.env` 中以 `WEBCAM_*` 覆寫）：

| 設定項目 | 環境變數 | 預設值 | 說明 |
| --- | --- | ---: | --- |
| 掃描間隔 | `WEBCAM_SAMPLE_INTERVAL_SECONDS` | 30 秒 | 影格擷取分析頻率 |
| 最低信心度 | `WEBCAM_ALERT_CONFIDENCE` | 80% | 辨識結果必須達到的信心值 |
| 連續一致次數 | `WEBCAM_ALERT_CONSECUTIVE_MATCHES` | 3 次 | 相同結果連續命中門檻（防誤報） |
| 警報冷卻時間 | `WEBCAM_ALERT_COOLDOWN_SECONDS` | 900 秒 | 相同病蟲害告警後冷卻靜音時間 |
| 影像尺寸限制 | `WEBCAM_MIN_IMAGE_WIDTH` / `HEIGHT` | 320 x 240 | 排除過小或模糊之無效影格 |
| 影像容量上限 | `WEBCAM_MAX_IMAGE_BYTES` | 8 MiB | 傳輸最大允許上限 |

---

## Android 客戶端配置

在 `frontend/plantdoctor/local.properties` 設定連線之伺服器位址：

```properties
WIFI_HOST=192.168.1.100
```

- 若使用 **Android 模擬器**，系統預設自動導向 `10.0.2.2:8000`。
- 若使用 **實體手機**，請確保手機與主機處於同一個 Wi-Fi 區域網路，並填寫主機區域 IP。
- API 統一端點基礎前綴為 `/api/v1/`。

---

## 測試與資料庫維護

### 執行單元與業務邏輯測試

```powershell
python -m pytest test/test_tripartite_arbiter.py test/test_services.py test/test_webcam.py -q
```

### 資料庫 Migration 狀態

```powershell
# 檢視當前遷移頭部版本
python -m alembic heads

# 升級資料庫至最新結構
python -m alembic upgrade head
```

*目前最新 Alembic migration head 為 `c56b561c634c`。*
