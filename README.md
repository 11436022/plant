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

## 已實作流程與驗證範圍


以下為程式中已具備的流程，不代表已完成實機或正式環境驗收。測試證據、限制與待驗證項目另見[修正與驗證報告](documents/verification_report.md)。

- 帳號註冊、Email 驗證、登入、JWT 驗證與忘記密碼
- Android 拍照／相簿上傳、診斷確認、歷史紀錄、備註與使用者修正
- 作物、病害、蟲害參考資料庫；由維護者執行同步及匯入腳本
- 管理員登入後可查看統計、使用者列表，並新增、修正及刪除診斷紀錄；後台不是知識資料庫的完整 CRUD 介面
- RAG 參考資料檢索與 Gemini 圖片分析；索引未載入或版本不符時降級為不使用檢索
- AI 作物／病蟲害名稱白名單、信心門檻與作物關聯校驗
- AI 建議改由資料庫症狀與處置內容提供
- Webcam 定時掃描、分工作階段與區域的連續影格判定，以及聲音／瀏覽器／Android／Email 通知程式
- 瀏覽器 Webcam 警報紀錄、確認與刪除；Android 目前只有對應 API 宣告，尚無警報管理畫面

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
| **管理員登入** | `http://localhost:8000/admin/login` | 管理員專屬登入頁面 |
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

SMTP 同時影響註冊驗證及重設密碼。未完成信箱驗證的帳號不能登入；`email_sent=true` 只表示寄送呼叫成功，不保證收件。管理後台只允許資料庫角色為 `admin` 且已驗證信箱的帳號，支援 JWT 或 HttpOnly、SameSite=Strict 登入 Cookie。正式部署須使用 HTTPS，並設定足夠長且隨機的 JWT 密鑰。

建立資料庫後執行 migration 與基礎資料匯入：

```powershell
# 執行資料庫 Migration 至最新版本
python -m alembic upgrade head

# 匯入作物、病蟲害官方基本資料
python seed.py

# 建立 FAISS 向量知識庫索引
python build_knowledge_base.py
```

先備份既有資料庫，並在隔離環境驗證升級。新增遷移 `d42a91c8e510` 允許未驗證時間為空，並加入診斷來源快照、複核狀態與監控識別欄位；舊紀錄預設為待複核，不能回填不存在的來源。不要將舊的 `init_db.sql` 快照與 Alembic 初始化流程混用。本次未對正式 MySQL 執行遷移。

RAG 建庫只讀取 `data.json` 中具有完整來源欄位的病蟲害紀錄，不再讀入專題手冊。`knowledge_content.json` 保存建庫時間、語料及索引雜湊、模型版本與來源。舊格式索引須重新建立；建庫會呼叫 Gemini embedding API，須確認額度與費用。

更新已存在的診斷回傳資料庫：

```powershell
git pull --rebase origin main
python -m alembic upgrade head
python seed.py
```

`seed.py` 會依「作物 + 病害／蟲害名稱」更新或新增資料，不會清空帳號、日記、歷史診斷與 webcam 警報。需要重新取得農業部最新公開資料時，先執行 `python update_reference_data.py`，確認輸出筆數後再執行 migration 與 seed。

啟動 FastAPI：

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


瀏覽器擷取整幅畫面；Android `WebcamActivity` 提供單株及多區域裁切。每次啟動產生工作階段識別碼，多區域另傳區域識別碼；後端依使用者、工作階段及區域分開累計。Android 只依後端新建的警報發出通知，停止或切換監控後忽略舊回應。舊客戶端未傳識別碼時使用相容預設值，不能宣稱具有多區域隔離。

預設警報條件：

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

1. 圖片格式、容量、解析度與基本畫面資訊檢查。
2. 作物名稱必須完全符合資料庫白名單。
3. 病害或蟲害名稱必須完全符合資料庫白名單。
4. 病蟲害必須確實隸屬於辨識出的作物。
5. 信心值不足時回傳「無法判定」，不提供施藥指示。
6. 症狀與處置內容由資料庫覆蓋 Gemini 生成文字。
7. 可自動採用的病蟲害資料必須包含來源名稱、網址與來源紀錄 ID。
8. 沒有可追溯來源的舊資料會標記 `requires_review=true`，不觸發 webcam 自動警報。
9. Webcam 必須連續多張影格得到相同結果才觸發警報。

一般上傳與 Webcam 共用圖片解碼、MIME 對照、容量、最低尺寸及基本畫面資訊檢查。一般上傳也要求 JWT；分析後先回傳 `prediction_id`，本人在 15 分鐘內確認才建立正式歷史紀錄。未知或需複核結果可以保存，但保留警示且不觸發自動警報。病蟲害來源、信心值及複核狀態保存為當時快照，Android 結果及歷史畫面保留這些欄位。

目前診斷暫存與監控累計使用程序內記憶體，需以單一 worker 運行；重啟會失去待確認資料及連續計數。過期診斷在下次上傳或確認時清理，不是分散式持久化佇列。App 與管理後台的使用者修正為個人註記，不會取代原始建議或構成專業複核。舊版 PATCH 若直接修改作物或狀態，會重新校驗作物與病蟲害關聯、更新建議及來源、清空信心值並標記需複核，不是重新呼叫模型。

Webcam 警報在回應資料準備完成後提交資料庫，再獨立嘗試寄信。寄送失敗不刪除已保存的警報及圖片；若提交結果不明，會保留圖片供維護者核對，可能留下尚未關聯紀錄的圖片，不能直接批次刪除。

這些機制能降低幻覺與誤報，但影像 AI 不能保證 100% 正確。高風險處置、農藥選擇與劑量仍應由農業專業人員確認。

目前診斷資料以農業部重要農業害蟲診斷圖鑑及樹木病蟲害診斷案例為主要官方來源。樹木案例只採用「病害／蟲害」且經樣本檢驗或現地診察的紀錄；含歷史藥劑濃度、稀釋倍數或施用方式的建議不直接回傳，以免過期用法被誤認為現行核准處方。API 診斷結果會包含 `reference_source`、`reference_url` 與 `reference_record_id` 供前端或人工查核。

## Android 設定

先安裝 Android SDK，並由 Android Studio 設定 SDK 路徑或在 `frontend/plantdoctor/local.properties` 填寫有效的 `sdk.dir`；同一檔案再設定後端主機：

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
python -m pytest test -q
node --test test/webcam_browser_regressions.cjs
```

### 資料庫 Migration 狀態

```powershell
# 檢視當前遷移頭部版本
python -m alembic heads

# 升級資料庫至最新結構
python -m alembic upgrade head
```

目前 migration head 為 `d42a91c8e510`。後端測試使用隔離 SQLite、實際 FAISS 索引，以及替代的 AI／向量與郵件服務；MySQL 僅做離線 SQL 編譯檢查。瀏覽器測試執行頁面原始 JavaScript，但使用替代的頁面與相機介面，不是實際瀏覽器操作。兩者均不代表 MySQL、Gemini、相機或 SMTP 收件已驗收。

Android 契約測試：在已安裝 Android SDK 的環境，於 `frontend/plantdoctor` 執行 `gradlew.bat :app:testDebugUnitTest`。本次環境缺少 Android SDK，未能完成此建置。

## 參考資料限制

來源網址可能指向整份資料集，不保證直達單一案例。新的樹木資料同步以原始資料列內容產生 `tree-local-*` 指紋，這不是官方案例編號；`reference_sync` 記錄處理時間與原始輸入雜湊，未提供的原始發表日期保持未知。更新腳本不代表正式資料庫或既有索引已更新，仍須由維護者備份、同步、匯入並重新建庫。
