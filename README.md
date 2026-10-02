# Plant Doctor 植物病蟲害診斷系統

Plant Doctor 是一套以 Android App 與瀏覽器 webcam 為前端、FastAPI 為後端、MySQL 為資料庫，並使用 Google Gemini 與本地知識庫協助辨識的植物病蟲害系統。

## 已實作流程與驗證範圍

以下為程式中已具備的流程，不代表已完成實機或正式環境驗收。測試證據、限制與待驗證項目另見 `documents/verification_report.md`。

- 帳號註冊、Email 驗證、登入、JWT 驗證與忘記密碼
- Android 拍照／相簿上傳、診斷確認、歷史紀錄、備註與使用者修正
- 作物、病害、蟲害參考資料庫；由維護者執行同步及匯入腳本
- 管理員登入後可查看統計、使用者列表，並新增、修正及刪除診斷紀錄；後台不是知識資料庫的完整 CRUD 介面
- RAG 參考資料檢索與 Gemini 圖片分析；索引未載入或版本不符時降級為不使用檢索
- AI 作物／病蟲害名稱白名單、信心門檻與作物關聯校驗
- AI 建議改由資料庫症狀與處置內容提供
- Webcam 定時掃描、分工作階段與區域的連續影格判定，以及聲音／瀏覽器／Android／Email 通知程式
- Webcam 警報紀錄、確認與刪除

## 系統架構

```text
Android App ─────────────┐
                        ├── HTTP/JWT ── FastAPI ── MySQL
Browser Webcam Console ─┘                 │
                                         ├── Gemini Image Analysis
                                         ├── FAISS RAG Knowledge Base
                                         └── SMTP Alert Email
```

主要入口：

| 功能 | 網址 |
| --- | --- |
| API 文件 | `http://localhost:8000/docs` |
| Webcam 自動警報 | `http://localhost:8000/webcam` |
| 管理後台 | `http://localhost:8000/admin/` |
| 管理員登入 | `http://localhost:8000/admin/login` |
| 健康檢查 | `http://localhost:8000/` |

## 環境需求

- Python 3.10 以上
- MySQL 8
- Gemini API Key
- Chrome、Edge 或其他支援 `getUserMedia` 的瀏覽器
- Android Studio（需要建置 Android App 時）

瀏覽器只允許在 `localhost` 或 HTTPS 安全來源使用 webcam。跨電腦部署時，請使用 HTTPS 反向代理開啟 `/webcam`。

## 後端安裝

```powershell
git clone https://github.com/11436022/plant.git
cd plant
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

編輯 `.env`，至少設定：

```dotenv
GEMINI_API_KEY=your_gemini_api_key
DB_HOST=127.0.0.1
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_NAME=plant_db
JWT_SECRET_KEY=replace_with_a_long_random_secret
FRONTEND_BASE_URL=http://127.0.0.1:8000
PUBLIC_BASE_URL=http://127.0.0.1:8000
```

Email 警報需要再設定 `SMTP_HOST`、`SMTP_USERNAME`、`SMTP_PASSWORD` 與 `SMTP_FROM_EMAIL`。未設定 SMTP 時，畫面與資料庫警報仍會正常運作，紀錄會顯示 Email 未寄送。

SMTP 同時影響註冊驗證及重設密碼。未完成信箱驗證的帳號不能登入；`email_sent=true` 只表示寄送呼叫成功，不保證收件。管理後台只允許資料庫角色為 `admin` 且已驗證信箱的帳號，支援 JWT 或 HttpOnly、SameSite=Strict 登入 Cookie。正式部署須使用 HTTPS，並設定足夠長且隨機的 JWT 密鑰。

建立資料庫後執行 migration 與基礎資料匯入：

```powershell
python -m alembic upgrade head
python seed.py
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

Docker 啟動：

```powershell
docker compose up --build
```

Docker 連接主機 MySQL 時，將 `.env` 的 `DB_HOST` 改為 `host.docker.internal`。

## Webcam 自動警報

1. 開啟 `http://localhost:8000/webcam` 並使用既有帳號登入。
2. 選擇攝影機，按「開啟」，再按「監控」。
3. 系統依設定間隔擷取影格並送到受 JWT 保護的 API。
4. 相同且已由資料庫校驗的病蟲害連續達門檻後，才建立警報。
5. 警報會保存影像與時間，並嘗試發出聲音、瀏覽器通知及 Email。

瀏覽器擷取整幅畫面；Android `WebcamActivity` 提供單株及多區域裁切。每次啟動產生工作階段識別碼，多區域另傳區域識別碼；後端依使用者、工作階段及區域分開累計。Android 只依後端新建的警報發出通知，停止或切換監控後忽略舊回應。舊客戶端未傳識別碼時使用相容預設值，不能宣稱具有多區域隔離。

預設警報條件：

| 設定 | 預設值 |
| --- | ---: |
| 掃描間隔 | 30 秒 |
| 最低信心值 | 80% |
| 連續一致影格 | 3 次 |
| 相同警報冷卻 | 900 秒 |
| 最低影像尺寸 | 320 x 240 |
| 最大影像大小 | 8 MiB |

以上設定可在 `.env` 以 `WEBCAM_*` 變數調整。瀏覽器可改掃描間隔，但信心、連續次數與冷卻門檻由後端控制，避免前端繞過安全規則。

## 防止 AI 幻覺

系統不把 Gemini 回傳內容直接視為事實，診斷必須依序通過：

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

目前診斷暫存與監控累計使用程序內記憶體，需以單一 worker 運行；重啟會失去待確認資料及連續計數。過期診斷在下次上傳或確認時清理，不是分散式持久化佇列。使用者修正為個人註記，不會取代原始建議或構成專業複核；管理後台的修正也不改寫原始辨識依據。

這些機制能降低幻覺與誤報，但影像 AI 不能保證 100% 正確。高風險處置、農藥選擇與劑量仍應由農業專業人員確認。

目前診斷資料以農業部重要農業害蟲診斷圖鑑及樹木病蟲害診斷案例為主要官方來源。樹木案例只採用「病害／蟲害」且經樣本檢驗或現地診察的紀錄；含歷史藥劑濃度、稀釋倍數或施用方式的建議不直接回傳，以免過期用法被誤認為現行核准處方。API 診斷結果會包含 `reference_source`、`reference_url` 與 `reference_record_id` 供前端或人工查核。

## Android 設定

在 `frontend/plantdoctor/local.properties` 設定後端主機：

```properties
WIFI_HOST=192.168.1.100
```

Android 模擬器會自動使用 `10.0.2.2:8000`；實體裝置與後端需位於可互通的網路。API Base URL 為 `/api/v1/`。

## 測試

執行防幻覺與 webcam 安全測試：

```powershell
python -m pytest test/test_ai_validation.py test/test_reference_data.py test/test_seed.py test/test_webcam.py -q
```

檢查 Alembic migration：

```powershell
python -m alembic heads
python -m alembic upgrade head
```

目前 migration head 為 `d42a91c8e510`。完整後端測試可執行 `python -m pytest test -q`；測試使用隔離 SQLite、模擬 AI 與郵件，不代表 MySQL、Gemini、相機或 SMTP 收件已驗收。

Android 契約測試：在已安裝 Android SDK 的環境，於 `frontend/plantdoctor` 執行 `gradlew.bat :app:testDebugUnitTest`。本次環境缺少 Android SDK，未能完成此建置。

## 參考資料限制

來源網址可能指向整份資料集，不保證直達單一案例。新的樹木資料同步以原始資料列內容產生 `tree-local-*` 指紋，這不是官方案例編號；`reference_sync` 記錄處理時間與原始輸入雜湊，未提供的原始發表日期保持未知。更新腳本不代表正式資料庫或既有索引已更新，仍須由維護者備份、同步、匯入並重新建庫。
