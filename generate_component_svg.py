# Generate system_component.svg (圖 7-3-1 元件圖)
svg_content = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 760" width="1200" height="760">
  <defs>
    <style>
      .title { font-family: 'Microsoft JhengHei', 'PingFang TC', sans-serif; font-size: 20px; font-weight: bold; fill: #0f172a; }
      .pkg-title { font-family: 'Microsoft JhengHei', 'PingFang TC', sans-serif; font-size: 13px; font-weight: bold; fill: #1e293b; }
      .comp-title { font-family: 'Microsoft JhengHei', 'PingFang TC', sans-serif; font-size: 12px; font-weight: bold; fill: #0f172a; }
      .comp-desc { font-family: 'Microsoft JhengHei', 'PingFang TC', sans-serif; font-size: 10px; fill: #64748b; }
      .stereotype { font-family: 'Consolas', 'Courier New', monospace; font-size: 10px; font-style: italic; fill: #2563eb; }
      .interface-text { font-family: 'Consolas', monospace; font-size: 10px; fill: #475569; text-anchor: middle; }
      
      .subsystem-bg { fill: #f8fafc; stroke: #94a3b8; stroke-width: 1.5; rx: 6; ry: 6; }
      .subsystem-header { fill: #e2e8f0; stroke: #94a3b8; stroke-width: 1.5; }
      
      .comp-box { fill: #ffffff; stroke: #3b82f6; stroke-width: 1.5; rx: 4; ry: 4; filter: drop-shadow(0 2px 4px rgba(0,0,0,0.05)); }
      .ai-comp-box { fill: #f0fdf4; stroke: #16a34a; stroke-width: 1.5; rx: 4; ry: 4; filter: drop-shadow(0 2px 4px rgba(0,0,0,0.05)); }
      .db-comp-box { fill: #fffbeb; stroke: #d97706; stroke-width: 1.5; rx: 4; ry: 4; filter: drop-shadow(0 2px 4px rgba(0,0,0,0.05)); }
      .cloud-comp-box { fill: #f5f3ff; stroke: #8b5cf6; stroke-width: 1.5; rx: 4; ry: 4; filter: drop-shadow(0 2px 4px rgba(0,0,0,0.05)); }
      
      .comp-icon-rect { fill: #ffffff; stroke: #3b82f6; stroke-width: 1.2; }
      
      .line { stroke: #334155; stroke-width: 1.3; fill: none; marker-end: url(#arrow); }
      .dash-line { stroke: #64748b; stroke-width: 1.3; stroke-dasharray: 4,4; fill: none; marker-end: url(#arrow); }
    </style>
    <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M 0 1 L 10 5 L 0 9 z" fill="#334155" />
    </marker>
    <!-- Component Icon Pattern -->
    <g id="comp-icon">
      <rect x="0" y="0" width="16" height="14" fill="#eff6ff" stroke="#3b82f6" stroke-width="1" />
      <rect x="-3" y="2" width="6" height="3" fill="#ffffff" stroke="#3b82f6" stroke-width="0.8" />
      <rect x="-3" y="8" width="6" height="3" fill="#ffffff" stroke="#3b82f6" stroke-width="0.8" />
    </g>
  </defs>

  <!-- Background -->
  <rect width="100%" height="100%" fill="#ffffff" />

  <!-- Diagram Title -->
  <text x="600" y="32" class="title" text-anchor="middle">圖 7-3-1 系統架構元件圖 (Component Diagram)</text>

  <!-- ================= CLIENT SUBSYSTEM ================= -->
  <g transform="translate(30, 60)">
    <rect width="280" height="660" class="subsystem-bg" />
    <path d="M 0 6 Q 0 0 6 0 L 274 0 Q 280 0 280 6 L 280 30 L 0 30 Z" class="subsystem-header" />
    <text x="15" y="20" class="pkg-title">客戶端元件 (Client Subsystem)</text>

    <!-- Component 1: Android UI -->
    <g transform="translate(15, 45)">
      <rect width="250" height="95" class="comp-box" />
      <use href="#comp-icon" x="225" y="10" />
      <text x="12" y="22" class="stereotype">&lt;&lt;component&gt;&gt;</text>
      <text x="12" y="38" class="comp-title">Android UI 元件群</text>
      <text x="12" y="55" class="comp-desc">• 診斷拍照 / 歷史瀏覽 / 備忘編輯</text>
      <text x="12" y="70" class="comp-desc">• 糾錯反饋彈窗 / 警報推播介面</text>
      <text x="12" y="85" class="comp-desc">• ViewModel 狀態與生命週期感知</text>
    </g>

    <!-- Component 2: Retrofit Network Client -->
    <g transform="translate(15, 160)">
      <rect width="250" height="90" class="comp-box" />
      <use href="#comp-icon" x="225" y="10" />
      <text x="12" y="22" class="stereotype">&lt;&lt;component&gt;&gt;</text>
      <text x="12" y="38" class="comp-title">REST API 客戶端元件</text>
      <text x="12" y="55" class="comp-desc">• Retrofit2 HTTP 介面抽象封裝</text>
      <text x="12" y="70" class="comp-desc">• OkHttp 攔截器 (JWT 注入與刷新)</text>
      <text x="12" y="85" class="comp-desc">• Multipart/form-data 影像分塊傳輸</text>
    </g>

    <!-- Component 3: Admin Web Dashboard -->
    <g transform="translate(15, 275)">
      <rect width="250" height="95" class="comp-box" />
      <use href="#comp-icon" x="225" y="10" />
      <text x="12" y="22" class="stereotype">&lt;&lt;component&gt;&gt;</text>
      <text x="12" y="38" class="comp-title">管理者儀表板元件</text>
      <text x="12" y="55" class="comp-desc">• HTML5 / Jinja2 / Vue 前台介面</text>
      <text x="12" y="70" class="comp-desc">• 診斷日誌全站檢閱與單筆刪除</text>
      <text x="12" y="85" class="comp-desc">• 糾錯回饋審查與 JSONL 標註匯出</text>
    </g>

    <!-- Component 4: Webcam Monitoring Component -->
    <g transform="translate(15, 395)">
      <rect width="250" height="95" class="comp-box" />
      <use href="#comp-icon" x="225" y="10" />
      <text x="12" y="22" class="stereotype">&lt;&lt;component&gt;&gt;</text>
      <text x="12" y="38" class="comp-title">Webcam 串流監控元件</text>
      <text x="12" y="55" class="comp-desc">• MediaDevices 影像串流擷取</text>
      <text x="12" y="70" class="comp-desc">• Canvas 局部區域感興趣特徵選取</text>
      <text x="12" y="85" class="comp-desc">• 定時自動影格上傳與警報輪詢</text>
    </g>

    <!-- Component 5: Local Cache & Storage -->
    <g transform="translate(15, 515)">
      <rect width="250" height="95" class="comp-box" />
      <use href="#comp-icon" x="225" y="10" />
      <text x="12" y="22" class="stereotype">&lt;&lt;component&gt;&gt;</text>
      <text x="12" y="38" class="comp-title">客戶端本機儲存元件</text>
      <text x="12" y="55" class="comp-desc">• EncryptedSharedPreferences (Token)</text>
      <text x="12" y="70" class="comp-desc">• 拍照影像暫存目錄快取</text>
      <text x="12" y="85" class="comp-desc">• 離線狀態快取與同步佇列</text>
    </g>
  </g>

  <!-- ================= BACKEND SUBSYSTEM ================= -->
  <g transform="translate(350, 60)">
    <rect width="520" height="660" class="subsystem-bg" />
    <path d="M 0 6 Q 0 0 6 0 L 514 0 Q 520 0 520 6 L 520 30 L 0 30 Z" class="subsystem-header" />
    <text x="15" y="20" class="pkg-title">FastAPI 後端核心元件群 (Backend Subsystem)</text>

    <!-- Backend Comp 1: API Gateway & Router -->
    <g transform="translate(15, 45)">
      <rect width="490" height="85" class="comp-box" />
      <use href="#comp-icon" x="465" y="10" />
      <text x="12" y="22" class="stereotype">&lt;&lt;component&gt;&gt;</text>
      <text x="12" y="38" class="comp-title">API 路由閘道元件 (API Gateway &amp; Router)</text>
      <text x="12" y="55" class="comp-desc">• 集中處理 HTTP 請求路徑分發 (Auth, Prediction, Diaries, Feedback, Webcam, Admin)</text>
      <text x="12" y="70" class="comp-desc">• CORS 跨域安全配置、全域異常捕獲與 Pydantic 請求資料型別校驗</text>
    </g>

    <!-- Backend Comp 2: Auth & Security -->
    <g transform="translate(15, 145)">
      <rect width="490" height="75" class="comp-box" />
      <use href="#comp-icon" x="465" y="10" />
      <text x="12" y="22" class="stereotype">&lt;&lt;component&gt;&gt;</text>
      <text x="12" y="38" class="comp-title">身分認證與安全授權元件 (Auth &amp; Security)</text>
      <text x="12" y="55" class="comp-desc">• Bcrypt 密碼雜湊安全演算、JWT (HS256) 權杖簽署與過期檢驗</text>
      <text x="12" y="70" class="comp-desc">• RBAC 角色存取控管 (User 業務功能 vs. Admin 管理員儀表板)</text>
    </g>

    <!-- Backend Comp 3: Dual-Model Orchestrator -->
    <g transform="translate(15, 235)">
      <rect width="490" height="95" class="ai-comp-box" />
      <use href="#comp-icon" x="465" y="10" />
      <text x="12" y="22" class="stereotype" fill="#15803d">&lt;&lt;core component&gt;&gt;</text>
      <text x="12" y="38" class="comp-title">多模型決策仲裁元件 (Dual-Model Orchestrator)</text>
      <text x="12" y="55" class="comp-desc">• 非同步協同調度 Gemini 2.5 Flash 雲端多模態與本地自訓 ConvNet 模型</text>
      <text x="12" y="70" class="comp-desc">• 決策仲裁核心：標籤一致性加權、微觀病徵互補校準與衝突過濾</text>
      <text x="12" y="85" class="comp-desc">• 嚴格執行 70% 信心度閾值檢驗，未達標自動標註「需專業人工複核」</text>
    </g>

    <!-- Backend Comp 4: Local ConvNet Inference -->
    <g transform="translate(15, 345)">
      <rect width="240" height="85" class="ai-comp-box" />
      <use href="#comp-icon" x="215" y="10" />
      <text x="10" y="22" class="stereotype" fill="#15803d">&lt;&lt;local inference&gt;&gt;</text>
      <text x="10" y="38" class="comp-title">本地 ConvNet 推論核心</text>
      <text x="10" y="55" class="comp-desc">• 特定作物卷積網路分類</text>
      <text x="10" y="70" class="comp-desc">• 微觀病斑局部特徵辨識</text>
      <text x="10" y="85" class="comp-desc">• 零雲端託管端點費用</text>
    </g>

    <!-- Backend Comp 5: FAISS Vector RAG -->
    <g transform="translate(265, 345)">
      <rect width="240" height="85" class="ai-comp-box" />
      <use href="#comp-icon" x="215" y="10" />
      <text x="10" y="22" class="stereotype" fill="#15803d">&lt;&lt;knowledge rag&gt;&gt;</text>
      <text x="10" y="38" class="comp-title">FAISS 向量檢索核心</text>
      <text x="10" y="55" class="comp-desc">• 農業部開放資料高維索引</text>
      <text x="10" y="70" class="comp-desc">• 語意相似度檢索增強 (RAG)</text>
      <text x="10" y="85" class="comp-desc">• 官方處置方針客觀校驗</text>
    </g>

    <!-- Backend Comp 6: Diary & Feedback Manager -->
    <g transform="translate(15, 445)">
      <rect width="490" height="80" class="comp-box" />
      <use href="#comp-icon" x="465" y="10" />
      <text x="12" y="22" class="stereotype">&lt;&lt;component&gt;&gt;</text>
      <text x="12" y="38" class="comp-title">植物日誌與反饋管理元件 (Diary &amp; Feedback Manager)</text>
      <text x="12" y="55" class="comp-desc">• 二階段日誌持久化：快取生成 (prediction_id) ➜ 使用者確認儲存</text>
      <text x="12" y="70" class="comp-desc">• 支援個人備忘筆記 (user_note) 獨立編輯與使用者糾錯回饋提報</text>
    </g>

    <!-- Backend Comp 7: Webcam Alert Engine -->
    <g transform="translate(15, 540)">
      <rect width="490" height="75" class="comp-box" />
      <use href="#comp-icon" x="465" y="10" />
      <text x="12" y="22" class="stereotype">&lt;&lt;component&gt;&gt;</text>
      <text x="12" y="38" class="comp-title">Webcam 時序警報引擎 (Webcam Temporal Alert Engine)</text>
      <text x="12" y="55" class="comp-desc">• 連續影格時序一致性判定（過濾光影晃動雜訊，杜絕誤報）</text>
      <text x="12" y="70" class="comp-desc">• 觸發高危病害警報並自動持久化至 webcam_alert 資料表</text>
    </g>
  </g>

  <!-- ================= EXTERNAL SUBSYSTEM ================= -->
  <g transform="translate(910, 60)">
    <rect width="260" height="660" class="subsystem-bg" />
    <path d="M 0 6 Q 0 0 6 0 L 254 0 Q 260 0 260 6 L 260 30 L 0 30 Z" class="subsystem-header" />
    <text x="15" y="20" class="pkg-title">資料持久化與外部雲端服務</text>

    <!-- Database Component -->
    <g transform="translate(15, 45)">
      <rect width="230" height="175" class="db-comp-box" />
      <use href="#comp-icon" x="205" y="10" />
      <text x="12" y="22" class="stereotype" fill="#b45309">&lt;&lt;database persistence&gt;&gt;</text>
      <text x="12" y="38" class="comp-title">MySQL 8.0 資料庫元件</text>
      <text x="12" y="58" class="comp-desc">8 大關聯式實體模型：</text>
      <text x="12" y="75" class="comp-desc">• user (帳號權限)</text>
      <text x="12" y="90" class="comp-desc">• user_one_time_tokens</text>
      <text x="12" y="105" class="comp-desc">• crop / disease / pests</text>
      <text x="12" y="120" class="comp-desc">• plant_diary (含 user_note)</text>
      <text x="12" y="135" class="comp-desc">• webcam_alert (警報日誌)</text>
      <text x="12" y="150" class="comp-desc">• diagnosis_feedback (回饋)</text>
      <text x="12" y="168" class="comp-desc">透過 SQLAlchemy 連線池存取</text>
    </g>

    <!-- Gemini Cloud AI Component -->
    <g transform="translate(15, 240)">
      <rect width="230" height="120" class="cloud-comp-box" />
      <use href="#comp-icon" x="205" y="10" />
      <text x="12" y="22" class="stereotype" fill="#7c3aed">&lt;&lt;cloud service&gt;&gt;</text>
      <text x="12" y="38" class="comp-title">Google Gemini API 元件</text>
      <text x="12" y="58" class="comp-desc">• Gemini 2.5 Flash 旗艦模型</text>
      <text x="12" y="73" class="comp-desc">• google-genai 官方 SDK</text>
      <text x="12" y="88" class="comp-desc">• 多模態影像病理特徵分析</text>
      <text x="12" y="103" class="comp-desc">• JSON Schema 結構化輸出</text>
    </g>

    <!-- SMTP Mail Component -->
    <g transform="translate(15, 380)">
      <rect width="230" height="110" class="cloud-comp-box" />
      <use href="#comp-icon" x="205" y="10" />
      <text x="12" y="22" class="stereotype" fill="#7c3aed">&lt;&lt;cloud service&gt;&gt;</text>
      <text x="12" y="38" class="comp-title">Google SMTP 郵件元件</text>
      <text x="12" y="58" class="comp-desc">• Gmail SMTP TLS 通訊協定</text>
      <text x="12" y="73" class="comp-desc">• 信箱啟用驗證碼寄送</text>
      <text x="12" y="88" class="comp-desc">• 忘記密碼 Token 傳輸</text>
      <text x="12" y="103" class="comp-desc">• 緊急病害警報非同步推播</text>
    </g>
  </g>

  <!-- ================= INTER-SUBSYSTEM CONNECTORS ================= -->
  <!-- Client to Backend Gateway -->
  <line x1="280" y1="210" x2="365" y2="105" class="line" />
  <text x="320" y="150" class="interface-text">HTTP REST</text>

  <line x1="280" y1="320" x2="365" y2="105" class="line" />

  <line x1="280" y1="440" x2="365" y2="105" class="line" />

  <!-- Backend to Database -->
  <line x1="855" y1="485" x2="925" y2="135" class="line" />
  <text x="890" y="280" class="interface-text">SQLAlchemy</text>

  <!-- Backend to Gemini -->
  <line x1="855" y1="280" x2="925" y2="300" class="line" />
  <text x="890" y="270" class="interface-text">HTTPS</text>

  <!-- Backend to SMTP -->
  <line x1="855" y1="180" x2="925" y2="435" class="line" />
  <text x="890" y="375" class="interface-text">SMTP 587</text>

</svg>
"""

with open('documents/system_component.svg', 'w', encoding='utf-8') as f:
    f.write(svg_content.strip())
print("Created documents/system_component.svg")
