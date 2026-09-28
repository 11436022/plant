# Generate system_package.svg (圖 7-2-1 套件圖)
svg_content = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 820" width="1280" height="820">
  <defs>
    <style>
      .title { font-family: 'Microsoft JhengHei', 'PingFang TC', sans-serif; font-size: 20px; font-weight: bold; fill: #0f172a; }
      .pkg-header-text { font-family: 'Consolas', 'Courier New', monospace; font-size: 13px; font-weight: bold; fill: #1e293b; }
      .subpkg-title { font-family: 'Consolas', 'Courier New', monospace; font-size: 11px; font-weight: bold; fill: #1e293b; }
      .module-text { font-family: 'Consolas', 'Courier New', monospace; font-size: 11px; fill: #0f172a; }
      .module-desc { font-family: 'Microsoft JhengHei', sans-serif; font-size: 10px; fill: #64748b; }
      .dep-label { font-family: 'Consolas', monospace; font-size: 10px; fill: #2563eb; text-anchor: middle; }
      
      .pkg-tab { fill: #e2e8f0; stroke: #94a3b8; stroke-width: 1.2; }
      .pkg-body { fill: #f8fafc; stroke: #94a3b8; stroke-width: 1.2; rx: 4; ry: 4; filter: drop-shadow(0 2px 4px rgba(0,0,0,0.04)); }
      
      .subpkg-tab { fill: #dbeafe; stroke: #3b82f6; stroke-width: 1; }
      .subpkg-body { fill: #ffffff; stroke: #3b82f6; stroke-width: 1.2; rx: 3; ry: 3; }
      
      .service-tab { fill: #dcfce7; stroke: #10b981; stroke-width: 1; }
      .service-body { fill: #ffffff; stroke: #10b981; stroke-width: 1.2; rx: 3; ry: 3; }

      .ext-tab { fill: #fef3c7; stroke: #f59e0b; stroke-width: 1; }
      .ext-body { fill: #ffffff; stroke: #f59e0b; stroke-width: 1.2; rx: 3; ry: 3; }
      
      .dep-line { stroke: #64748b; stroke-width: 1.3; stroke-dasharray: 4,4; fill: none; marker-end: url(#arrow); }
      .http-line { stroke: #2563eb; stroke-width: 1.5; fill: none; marker-end: url(#blue-arrow); }
    </style>
    <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M 0 1 L 10 5 L 0 9 z" fill="#64748b" />
    </marker>
    <marker id="blue-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M 0 1 L 10 5 L 0 9 z" fill="#2563eb" />
    </marker>
  </defs>

  <!-- Background -->
  <rect width="100%" height="100%" fill="#ffffff" />

  <!-- Diagram Title -->
  <text x="640" y="32" class="title" text-anchor="middle">圖 7-2-1 系統軟體架構套件圖 (Package Diagram)</text>

  <!-- ================= PACKAGE 1: ANDROID APP ================= -->
  <g transform="translate(30, 60)">
    <!-- Package Tab -->
    <path d="M 0 0 L 160 0 L 175 22 L 0 22 Z" class="pkg-tab" />
    <text x="15" y="16" class="pkg-header-text">android.app</text>
    <!-- Package Body -->
    <rect y="22" width="300" height="710" class="pkg-body" />
    <text x="15" y="45" class="subpkg-title" fill="#475569">package com.example.plantdoctor</text>

    <!-- Subpkg: UI Activities -->
    <g transform="translate(15, 60)">
      <path d="M 0 0 L 110 0 L 120 18 L 0 18 Z" class="subpkg-tab" />
      <text x="10" y="13" class="subpkg-title">.ui.activities</text>
      <rect y="18" width="270" height="135" class="subpkg-body" />
      <text x="12" y="38" class="module-text">• MainActivity.kt</text>
      <text x="135" y="38" class="module-desc">(主頁與導覽)</text>
      <text x="12" y="58" class="module-text">• DiagnosisActivity.kt</text>
      <text x="145" y="58" class="module-desc">(拍照與雙模型預覽)</text>
      <text x="12" y="78" class="module-text">• HistoryActivity.kt</text>
      <text x="135" y="78" class="module-desc">(日誌歷史與搜尋)</text>
      <text x="12" y="98" class="module-text">• AlertActivity.kt</text>
      <text x="135" y="98" class="module-desc">(Webcam 警報列表)</text>
      <text x="12" y="118" class="module-text">• FeedbackDialog.kt</text>
      <text x="135" y="118" class="module-desc">(糾錯反饋互動彈窗)</text>
      <text x="12" y="138" class="module-text">• LoginActivity.kt</text>
      <text x="135" y="138" class="module-desc">(帳號登入與信箱驗證)</text>
    </g>

    <!-- Subpkg: UI Adapters -->
    <g transform="translate(15, 230)">
      <path d="M 0 0 L 105 0 L 115 18 L 0 18 Z" class="subpkg-tab" />
      <text x="10" y="13" class="subpkg-title">.ui.adapters</text>
      <rect y="18" width="270" height="80" class="subpkg-body" />
      <text x="12" y="40" class="module-text">• DiaryAdapter.kt</text>
      <text x="140" y="40" class="module-desc">(植物日誌清單渲染)</text>
      <text x="12" y="62" class="module-text">• AlertAdapter.kt</text>
      <text x="140" y="62" class="module-desc">(Webcam 警報項目)</text>
      <text x="12" y="84" class="module-text">• TreatmentStepAdapter.kt</text>
      <text x="175" y="84" class="module-desc">(防治步驟清單)</text>
    </g>

    <!-- Subpkg: Network & API -->
    <g transform="translate(15, 345)">
      <path d="M 0 0 L 90 0 L 100 18 L 0 18 Z" class="subpkg-tab" />
      <text x="10" y="13" class="subpkg-title">.network</text>
      <rect y="18" width="270" height="100" class="subpkg-body" />
      <text x="12" y="40" class="module-text">• PlantApiService.kt</text>
      <text x="150" y="40" class="module-desc">(Retrofit2 介面定義)</text>
      <text x="12" y="62" class="module-text">• NetworkClient.kt</text>
      <text x="150" y="62" class="module-desc">(OkHttp3 單例工廠)</text>
      <text x="12" y="84" class="module-text">• AuthInterceptor.kt</text>
      <text x="150" y="84" class="module-desc">(JWT 標頭自動注入)</text>
      <text x="12" y="106" class="module-text">• ErrorHandler.kt</text>
      <text x="150" y="106" class="module-desc">(全域網路異常攔截)</text>
    </g>

    <!-- Subpkg: Data Models (DTO) -->
    <g transform="translate(15, 480)">
      <path d="M 0 0 L 110 0 L 120 18 L 0 18 Z" class="subpkg-tab" />
      <text x="10" y="13" class="subpkg-title">.data.models</text>
      <rect y="18" width="270" height="100" class="subpkg-body" />
      <text x="12" y="40" class="module-text">• AuthDTO.kt</text>
      <text x="140" y="40" class="module-desc">(登入/註冊請求響應)</text>
      <text x="12" y="62" class="module-text">• PredictionDTO.kt</text>
      <text x="140" y="62" class="module-desc">(診斷推論結果封裝)</text>
      <text x="12" y="84" class="module-text">• PlantDiaryDTO.kt</text>
      <text x="140" y="84" class="module-desc">(日誌與備忘筆記實體)</text>
      <text x="12" y="106" class="module-text">• FeedbackDTO.kt</text>
      <text x="140" y="106" class="module-desc">(糾錯反饋提交物件)</text>
    </g>

    <!-- Subpkg: Utils & Storage -->
    <g transform="translate(15, 615)">
      <path d="M 0 0 L 80 0 L 90 18 L 0 18 Z" class="subpkg-tab" />
      <text x="10" y="13" class="subpkg-title">.utils</text>
      <rect y="18" width="270" height="85" class="subpkg-body" />
      <text x="12" y="40" class="module-text">• TokenManager.kt</text>
      <text x="140" y="40" class="module-desc">(EncryptedSharedPref)</text>
      <text x="12" y="62" class="module-text">• ImageCompressor.kt</text>
      <text x="140" y="62" class="module-desc">(上傳前圖片壓縮)</text>
      <text x="12" y="84" class="module-text">• CameraHelper.kt</text>
      <text x="140" y="84" class="module-desc">(CameraX 相機生命週期)</text>
    </g>
  </g>

  <!-- ================= PACKAGE 2: FASTAPI BACKEND ================= -->
  <g transform="translate(370, 60)">
    <!-- Package Tab -->
    <path d="M 0 0 L 190 0 L 205 22 L 0 22 Z" class="pkg-tab" />
    <text x="15" y="16" class="pkg-header-text">plant_backend.app</text>
    <!-- Package Body -->
    <rect y="22" width="560" height="710" class="pkg-body" />
    <text x="15" y="45" class="subpkg-title" fill="#475569">FastAPI 微服務架構核心套件 (Python 3.10)</text>

    <!-- Top Core: main.py & core -->
    <g transform="translate(15, 55)">
      <rect width="530" height="45" fill="#f1f5f9" stroke="#cbd5e1" rx="3" />
      <text x="15" y="27" class="module-text" font-weight="bold">main.py</text>
      <text x="75" y="27" class="module-desc">(ASGI 應用入口、CORS 中介軟體、靜態目錄掛載、全域異常過濾器)</text>
    </g>

    <!-- Subpkg: app.api.v1.routers -->
    <g transform="translate(15, 115)">
      <path d="M 0 0 L 140 0 L 150 18 L 0 18 Z" class="subpkg-tab" />
      <text x="10" y="13" class="subpkg-title">.api.v1.routers</text>
      <rect y="18" width="530" height="135" class="subpkg-body" />
      
      <!-- Router Modules (2 columns) -->
      <text x="15" y="42" class="module-text">• auth.py</text>
      <text x="135" y="42" class="module-desc">(註冊/登入/信箱認證/JWT)</text>

      <text x="280" y="42" class="module-text">• prediction.py</text>
      <text x="390" y="42" class="module-desc">(影像診斷與推論排程)</text>

      <text x="15" y="70" class="module-text">• diaries.py</text>
      <text x="135" y="70" class="module-desc">(日誌建立/查詢/備忘/刪除)</text>

      <text x="280" y="70" class="module-text">• feedback.py</text>
      <text x="390" y="70" class="module-desc">(使用者糾錯反饋與提報)</text>

      <text x="15" y="98" class="module-text">• webcam.py</text>
      <text x="135" y="98" class="module-desc">(即時影格接收與警報通知)</text>

      <text x="280" y="98" class="module-text">• admin.py</text>
      <text x="390" y="98" class="module-desc">(儀表板統計與審核匯出)</text>
      
      <text x="15" y="126" class="module-text">• crops.py</text>
      <text x="135" y="126" class="module-desc">(作物百科與病害資訊查詢)</text>

      <text x="280" y="126" class="module-text">• health.py</text>
      <text x="390" y="126" class="module-desc">(系統健康狀態與連線探針)</text>
    </g>

    <!-- Subpkg: app.services -->
    <g transform="translate(15, 275)">
      <path d="M 0 0 L 110 0 L 120 18 L 0 18 Z" class="service-tab" />
      <text x="10" y="13" class="subpkg-title">.services</text>
      <rect y="18" width="530" height="150" class="service-body" />
      
      <text x="15" y="42" class="module-text">• prediction_service.py</text>
      <text x="180" y="42" class="module-desc">(多模型決策仲裁、衝突過濾、70% 信心閾值檢核)</text>

      <text x="15" y="68" class="module-text">• gemini_service.py</text>
      <text x="180" y="68" class="module-desc">(Gemini 2.5 Flash 雲端多模態推論與結構化提示詞解析)</text>

      <text x="15" y="94" class="module-text">• local_convnet.py</text>
      <text x="180" y="94" class="module-desc">(本地自訓特定作物卷積神經網路微觀特徵分類, 零雲端成本)</text>

      <text x="15" y="120" class="module-text">• rag_service.py</text>
      <text x="180" y="120" class="module-desc">(FAISS 向量知識庫檢索增強與農業部開放資料交叉驗證)</text>

      <text x="15" y="146" class="module-text">• auth_service.py / email_service.py</text>
      <text x="270" y="146" class="module-desc">(密碼安全雜湊、Token 簽署與 SMTP 驗證碼寄送)</text>
    </g>

    <!-- Subpkg: app.db (SQLAlchemy ORM) -->
    <g transform="translate(15, 450)">
      <path d="M 0 0 L 70 0 L 80 18 L 0 18 Z" class="subpkg-tab" />
      <text x="10" y="13" class="subpkg-title">.db</text>
      <rect y="18" width="530" height="135" class="subpkg-body" />

      <text x="15" y="42" class="module-text">• session.py</text>
      <text x="120" y="42" class="module-desc">(SQLAlchemy 引擎連線池配置、SessionLocal 依賴注入工廠)</text>

      <text x="15" y="68" class="module-text">• models.py</text>
      <text x="120" y="68" class="module-desc">(定義 8 大資料表實體: user, crop, disease, pests,</text>
      <text x="120" y="84" class="module-desc"> plant_diary, webcam_alert, diagnosis_feedback, user_one_time_tokens)</text>

      <text x="15" y="110" class="module-text">• crud.py</text>
      <text x="120" y="110" class="module-desc">(封裝日誌 CRUD、個人備忘筆記更新、糾錯回饋審核與統計查詢)</text>

      <text x="15" y="132" class="module-text">• base.py</text>
      <text x="120" y="132" class="module-desc">(Base 宣告式中繼類別)</text>
    </g>

    <!-- Subpkg: app.core & app.schemas -->
    <g transform="translate(15, 610)">
      <rect width="255" height="95" fill="#f8fafc" stroke="#cbd5e1" rx="3" />
      <text x="15" y="25" class="subpkg-title">.core (系統配置與安全性)</text>
      <text x="15" y="48" class="module-text">• config.py (Pydantic BaseSettings)</text>
      <text x="15" y="68" class="module-text">• security.py (bcrypt / JWT HS256)</text>
      <text x="15" y="88" class="module-desc">支援 .env 環境設定與安全金鑰管理</text>

      <g transform="translate(275, 0)">
        <rect width="255" height="95" fill="#f8fafc" stroke="#cbd5e1" rx="3" />
        <text x="15" y="25" class="subpkg-title">.schemas (Pydantic DTO 規格)</text>
        <text x="15" y="48" class="module-text">• user.py / token.py / diary.py</text>
        <text x="15" y="68" class="module-text">• prediction.py / feedback.py</text>
        <text x="15" y="88" class="module-desc">強型別資料校驗與序列化定義</text>
      </g>
    </g>
  </g>

  <!-- ================= PACKAGE 3: EXTERNAL DEPENDENCIES ================= -->
  <g transform="translate(970, 60)">
    <!-- Package Tab -->
    <path d="M 0 0 L 160 0 L 175 22 L 0 22 Z" class="pkg-tab" />
    <text x="15" y="16" class="pkg-header-text">external_libs</text>
    <!-- Package Body -->
    <rect y="22" width="280" height="710" class="pkg-body" />
    <text x="15" y="45" class="subpkg-title" fill="#475569">核心依賴第三方函式庫群</text>

    <!-- AI & ML Libs -->
    <g transform="translate(15, 60)">
      <path d="M 0 0 L 120 0 L 130 18 L 0 18 Z" class="ext-tab" />
      <text x="10" y="13" class="subpkg-title">AI &amp; Deep Learning</text>
      <rect y="18" width="250" height="150" class="ext-body" />
      <text x="12" y="40" class="module-text">• google-genai</text>
      <text x="120" y="40" class="module-desc">(官方 GenAI SDK)</text>
      <text x="12" y="62" class="module-text">• torch</text>
      <text x="120" y="62" class="module-desc">(PyTorch 深度學習)</text>
      <text x="12" y="84" class="module-text">• torchvision</text>
      <text x="120" y="84" class="module-desc">(影像特徵預處理)</text>
      <text x="12" y="106" class="module-text">• faiss-cpu</text>
      <text x="120" y="106" class="module-desc">(Facebook 向量索引)</text>
      <text x="12" y="128" class="module-text">• sentence-transformers</text>
      <text x="12" y="148" class="module-desc">(農業開放資料嵌入向量生成)</text>
    </g>

    <!-- Web & Database Libs -->
    <g transform="translate(15, 240)">
      <path d="M 0 0 L 120 0 L 130 18 L 0 18 Z" class="ext-tab" />
      <text x="10" y="13" class="subpkg-title">Web &amp; Persistence</text>
      <rect y="18" width="250" height="145" class="ext-body" />
      <text x="12" y="40" class="module-text">• fastapi</text>
      <text x="110" y="40" class="module-desc">(高併發非同步 API)</text>
      <text x="12" y="62" class="module-text">• uvicorn</text>
      <text x="110" y="62" class="module-desc">(ASGI 網頁伺服器)</text>
      <text x="12" y="84" class="module-text">• sqlalchemy 2.0</text>
      <text x="125" y="84" class="module-desc">(ORM 資料庫對映)</text>
      <text x="12" y="106" class="module-text">• pymysql</text>
      <text x="110" y="106" class="module-desc">(MySQL 純 Python 驅動)</text>
      <text x="12" y="128" class="module-text">• pydantic v2</text>
      <text x="120" y="128" class="module-desc">(資料模型驗證解析)</text>
      <text x="12" y="150" class="module-text">• alembic</text>
      <text x="110" y="150" class="module-desc">(資料庫結構遷移維護)</text>
    </g>

    <!-- Security & Utility Libs -->
    <g transform="translate(15, 415)">
      <path d="M 0 0 L 120 0 L 130 18 L 0 18 Z" class="ext-tab" />
      <text x="10" y="13" class="subpkg-title">Security &amp; Utility</text>
      <rect y="18" width="250" height="110" class="ext-body" />
      <text x="12" y="40" class="module-text">• passlib[bcrypt]</text>
      <text x="135" y="40" class="module-desc">(密碼加密雜湊)</text>
      <text x="12" y="62" class="module-text">• python-jose[cryptography]</text>
      <text x="12" y="78" class="module-desc">(JWT 權杖簽發與驗證)</text>
      <text x="12" y="98" class="module-text">• pillow (PIL)</text>
      <text x="120" y="98" class="module-desc">(影像格式轉換與快取)</text>
      <text x="12" y="118" class="module-text">• jinja2</text>
      <text x="120" y="118" class="module-desc">(後台儀表板樣板引擎)</text>
    </g>
  </g>

  <!-- ================= INTER-PACKAGE CONNECTIONS ================= -->
  <!-- Android Network to FastAPI Routers -->
  <line x1="330" y1="420" x2="370" y2="215" class="http-line" />
  <text x="350" y="310" class="dep-label" transform="rotate(-65 350 310)">&lt;&lt;HTTPS / JSON&gt;&gt;</text>

  <!-- FastAPI Services to External AI -->
  <line x1="930" y1="365" x2="970" y2="175" class="dep-line" />
  <text x="955" y="270" class="dep-label" transform="rotate(-65 955 270)">&lt;&lt;import&gt;&gt;</text>

  <!-- FastAPI DB to External Persistence -->
  <line x1="930" y1="520" x2="970" y2="330" class="dep-line" />
  <text x="955" y="425" class="dep-label" transform="rotate(-65 955 425)">&lt;&lt;import&gt;&gt;</text>

</svg>
"""

with open('documents/system_package.svg', 'w', encoding='utf-8') as f:
    f.write(svg_content.strip())
print("Created documents/system_package.svg")
