import os

# Script to generate 5 modern UML 2.0 State Machine Diagrams for Chapter 7 (Section 7.4)

def generate_svg_auth():
    # 7-4-1 帳號註冊與認證登入 狀態圖
    return """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1100 680" width="1100" height="680">
  <defs>
    <style>
      .title { font-family: 'Microsoft JhengHei', sans-serif; font-size: 20px; font-weight: bold; fill: #0f172a; }
      .group-title { font-family: 'Microsoft JhengHei', sans-serif; font-size: 13px; font-weight: bold; fill: #1e293b; }
      .state-name { font-family: 'Microsoft JhengHei', sans-serif; font-size: 13px; font-weight: bold; fill: #0f172a; text-anchor: middle; }
      .action-text { font-family: 'Microsoft JhengHei', sans-serif; font-size: 10px; fill: #475569; }
      .transition-text { font-family: 'Microsoft JhengHei', sans-serif; font-size: 10px; fill: #1d4ed8; font-weight: 500; }
      .guard-text { font-family: 'Microsoft JhengHei', sans-serif; font-size: 9px; fill: #b91c1c; font-style: italic; }
      
      .composite-bg { fill: #f8fafc; stroke: #94a3b8; stroke-width: 1.5; stroke-dasharray: 6,4; rx: 8; ry: 8; }
      .composite-header { fill: #e2e8f0; stroke: #94a3b8; stroke-width: 1.5; }
      
      .state-box { fill: #ffffff; stroke: #2563eb; stroke-width: 1.5; rx: 6; ry: 6; filter: drop-shadow(0 2px 4px rgba(0,0,0,0.06)); }
      .state-header { fill: #eff6ff; stroke: #2563eb; stroke-width: 1.5; }
      
      .error-state-box { fill: #fef2f2; stroke: #dc2626; stroke-width: 1.5; rx: 6; ry: 6; }
      .error-state-header { fill: #fee2e2; stroke: #dc2626; stroke-width: 1.5; }
      
      .line { stroke: #334155; stroke-width: 1.3; fill: none; marker-end: url(#arrow); }
      .line-back { stroke: #64748b; stroke-width: 1.2; stroke-dasharray: 4,3; fill: none; marker-end: url(#arrow); }
    </style>
    <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M 0 1 L 10 5 L 0 9 z" fill="#334155" />
    </marker>
  </defs>

  <!-- Background -->
  <rect width="100%" height="100%" fill="#ffffff" />

  <!-- Diagram Title -->
  <text x="550" y="32" class="title" text-anchor="middle">圖 7-4-1 帳號註冊與認證登入 狀態圖 (State Diagram)</text>

  <!-- Initial State -->
  <circle cx="50" cy="180" r="8" fill="#0f172a" />
  <line x1="58" y1="180" x2="95" y2="180" class="line" />

  <!-- ================= COMPOSITE STATE 1: REGISTRATION ================= -->
  <g transform="translate(100, 60)">
    <rect width="450" height="580" class="composite-bg" />
    <path d="M 0 8 Q 0 0 8 0 L 442 0 Q 450 0 450 8 L 450 30 L 0 30 Z" class="composite-header" />
    <text x="15" y="20" class="group-title">狀態群組 1：帳號註冊與信箱驗證狀態 (Registration &amp; Verification)</text>

    <!-- State 1: 未註冊 -->
    <g transform="translate(30, 50)">
      <rect width="170" height="65" class="state-box" />
      <path d="M 0 6 Q 0 0 6 0 L 164 0 Q 170 0 170 6 L 170 24 L 0 24 Z" class="state-header" />
      <text x="85" y="17" class="state-name">未註冊 (Unregistered)</text>
      <text x="10" y="42" class="action-text">entry / 載入註冊表單</text>
      <text x="10" y="56" class="action-text">do / 輸入帳號、信箱、密碼</text>
    </g>

    <!-- Transition 1 -> 2 -->
    <line x1="200" y1="82" x2="255" y2="82" class="line" />
    <text x="228" y="75" class="transition-text" text-anchor="middle">點擊註冊</text>

    <!-- State 2: 驗證碼寄送中 -->
    <g transform="translate(260, 50)">
      <rect width="165" height="75" class="state-box" />
      <path d="M 0 6 Q 0 0 6 0 L 159 0 Q 165 0 165 6 L 165 24 L 0 24 Z" class="state-header" />
      <text x="82" y="17" class="state-name">寄送驗證碼 (Sending_OTP)</text>
      <text x="8" y="42" class="action-text">do / 查核信箱與帳號唯一性</text>
      <text x="8" y="56" class="action-text">do / 生成 6 位數安全 OTP</text>
      <text x="8" y="69" class="action-text">do / Gmail SMTP 發送驗證信</text>
    </g>

    <!-- Transition: 2 -> Error (Conflict) -->
    <line x1="342" y1="125" x2="342" y2="185" class="line" />
    <text x="348" y="160" class="guard-text">[信箱或帳號已存在]</text>

    <!-- State: 註冊失敗 -->
    <g transform="translate(260, 185)">
      <rect width="165" height="60" class="error-state-box" />
      <path d="M 0 6 Q 0 0 6 0 L 159 0 Q 165 0 165 6 L 165 22 L 0 22 Z" class="error-state-header" />
      <text x="82" y="16" class="state-name" fill="#991b1b">註冊失敗 (Reg_Failed)</text>
      <text x="10" y="38" class="action-text" fill="#b91c1c">entry / 顯示帳號衝突訊息</text>
      <text x="10" y="52" class="action-text" fill="#b91c1c">do / 提示使用者更換</text>
    </g>

    <!-- Loop back from Error to Unregistered -->
    <path d="M 260 215 L 115 215 L 115 115" class="line-back" />
    <text x="180" y="208" class="transition-text" text-anchor="middle">返回修正表單</text>

    <!-- Transition: 2 -> 3 (Success) -->
    <path d="M 342 50 L 342 35 L 115 35 L 115 270 L 115 295" class="line" />
    <text x="210" y="45" class="transition-text" text-anchor="middle">[驗證碼發送成功]</text>

    <!-- State 3: 等待信箱驗證 -->
    <g transform="translate(30, 295)">
      <rect width="170" height="75" class="state-box" />
      <path d="M 0 6 Q 0 0 6 0 L 164 0 Q 170 0 170 6 L 170 24 L 0 24 Z" class="state-header" />
      <text x="85" y="17" class="state-name">等待驗證 (Awaiting_OTP)</text>
      <text x="10" y="42" class="action-text">entry / 彈出 OTP 輸入框</text>
      <text x="10" y="56" class="action-text">do / 啟動 15 分鐘有效倒數</text>
      <text x="10" y="70" class="action-text">do / 填入 6 位數代碼送出</text>
    </g>

    <!-- Transition: 3 -> Error OTP -->
    <line x1="200" y1="332" x2="260" y2="332" class="line" />
    <text x="230" y="325" class="guard-text" text-anchor="middle">[過期或錯誤]</text>

    <!-- State: OTP 驗證失敗 -->
    <g transform="translate(260, 305)">
      <rect width="165" height="55" class="error-state-box" />
      <path d="M 0 6 Q 0 0 6 0 L 159 0 Q 165 0 165 6 L 165 22 L 0 22 Z" class="error-state-header" />
      <text x="82" y="16" class="state-name" fill="#991b1b">驗證失敗 (Token_Invalid)</text>
      <text x="10" y="38" class="action-text" fill="#b91c1c">do / 提示代碼不正確</text>
      <text x="10" y="50" class="action-text" fill="#b91c1c">do / 允許重新發送或輸入</text>
    </g>
    <path d="M 342 360 L 342 390 L 115 390 L 115 370" class="line-back" />

    <!-- Transition: 3 -> 4 (Activated) -->
    <line x1="115" y1="370" x2="115" y2="440" class="line" />
    <text x="120" y="410" class="transition-text">[Token 核對成功]</text>

    <!-- State 4: 帳號已啟用 -->
    <g transform="translate(30, 440)">
      <rect width="170" height="75" class="state-box" />
      <path d="M 0 6 Q 0 0 6 0 L 164 0 Q 170 0 170 6 L 170 24 L 0 24 Z" class="state-header" />
      <text x="85" y="17" class="state-name">帳號已啟用 (Activated)</text>
      <text x="10" y="42" class="action-text">entry / 更新 user.is_active=1</text>
      <text x="10" y="56" class="action-text">do / 刪除一次性 Token 紀錄</text>
      <text x="10" y="70" class="action-text">exit / 自動導向登入畫面</text>
    </g>
  </g>

  <!-- Inter-Composite Transition (Registration to Login) -->
  <path d="M 200 535 L 200 590 L 610 590 L 610 180 L 640 180" class="line" />
  <text x="400" y="583" class="transition-text" text-anchor="middle">註冊驗證完成 / 導向登入介面</text>

  <!-- ================= COMPOSITE STATE 2: AUTHENTICATION ================= -->
  <g transform="translate(620, 60)">
    <rect width="450" height="580" class="composite-bg" />
    <path d="M 0 8 Q 0 0 8 0 L 442 0 Q 450 0 450 8 L 450 30 L 0 30 Z" class="composite-header" />
    <text x="15" y="20" class="group-title">狀態群組 2：身分認證與會話授權狀態 (Authentication &amp; Session)</text>

    <!-- State 5: 未登入 -->
    <g transform="translate(25, 80)">
      <rect width="170" height="65" class="state-box" />
      <path d="M 0 6 Q 0 0 6 0 L 164 0 Q 170 0 170 6 L 170 24 L 0 24 Z" class="state-header" />
      <text x="85" y="17" class="state-name">未登入 (Logged_Out)</text>
      <text x="10" y="42" class="action-text">entry / 呈現登入表單介面</text>
      <text x="10" y="56" class="action-text">do / 輸入帳號與密碼</text>
    </g>

    <!-- Transition 5 -> 6 -->
    <line x1="195" y1="112" x2="255" y2="112" class="line" />
    <text x="225" y="105" class="transition-text" text-anchor="middle">點擊登入</text>

    <!-- State 6: 憑證校驗中 -->
    <g transform="translate(260, 80)">
      <rect width="165" height="75" class="state-box" />
      <path d="M 0 6 Q 0 0 6 0 L 159 0 Q 165 0 165 6 L 165 24 L 0 24 Z" class="state-header" />
      <text x="82" y="17" class="state-name">憑證校驗中 (Verifying)</text>
      <text x="8" y="42" class="action-text">do / 查詢帳號是否存在</text>
      <text x="8" y="56" class="action-text">do / Bcrypt 密碼雜湊比對</text>
      <text x="8" y="69" class="action-text">do / 查驗 is_active 啟用標記</text>
    </g>

    <!-- Transition: 6 -> Login Failed -->
    <line x1="342" y1="155" x2="342" y2="215" class="line" />
    <text x="348" y="190" class="guard-text">[密碼錯誤或未啟用]</text>

    <!-- State: 登入失敗 -->
    <g transform="translate(260, 215)">
      <rect width="165" height="60" class="error-state-box" />
      <path d="M 0 6 Q 0 0 6 0 L 159 0 Q 165 0 165 6 L 165 22 L 0 22 Z" class="error-state-header" />
      <text x="82" y="16" class="state-name" fill="#991b1b">登入失敗 (Login_Failed)</text>
      <text x="10" y="38" class="action-text" fill="#b91c1c">entry / 顯示憑證錯誤警告</text>
      <text x="10" y="52" class="action-text" fill="#b91c1c">do / 鎖定保護與重試限制</text>
    </g>
    <path d="M 260 245 L 110 245 L 110 145" class="line-back" />
    <text x="175" y="238" class="transition-text" text-anchor="middle">返回登入介面</text>

    <!-- Transition: 6 -> 7 (Success) -->
    <path d="M 342 80 L 342 45 L 110 45 L 110 295" class="line" />
    <text x="225" y="40" class="transition-text" text-anchor="middle">[密碼符合且已啟用]</text>

    <!-- State 7: 簽發 JWT Token -->
    <g transform="translate(25, 295)">
      <rect width="170" height="75" class="state-box" />
      <path d="M 0 6 Q 0 0 6 0 L 164 0 Q 170 0 170 6 L 170 24 L 0 24 Z" class="state-header" />
      <text x="85" y="17" class="state-name">簽發 Token (JWT_Issued)</text>
      <text x="10" y="42" class="action-text">do / 生成 HS256 簽署 Token</text>
      <text x="10" y="56" class="action-text">do / 載入 user_id 與角色權限</text>
      <text x="10" y="70" class="action-text">do / 注入 Token 效期 (7天)</text>
    </g>

    <!-- Transition: 7 -> 8 -->
    <line x1="110" y1="370" x2="110" y2="430" class="line" />
    <text x="115" y="405" class="transition-text">客戶端保存憑證</text>

    <!-- State 8: 已授權就緒 (Authenticated_Active) -->
    <g transform="translate(25, 430)">
      <rect width="210" height="90" class="state-box" />
      <path d="M 0 6 Q 0 0 6 0 L 204 0 Q 210 0 210 6 L 210 24 L 0 24 Z" class="state-header" />
      <text x="105" y="17" class="state-name">已授權就緒 (Auth_Active)</text>
      <text x="10" y="42" class="action-text">entry / 存入安全 SharedPreferences</text>
      <text x="10" y="56" class="action-text">do / 進入 App 主儀表板畫面</text>
      <text x="10" y="70" class="action-text">do / 開啟拍照診斷、日誌歷史功能</text>
      <text x="10" y="84" class="action-text">exit / 登出時註銷本機憑證</text>
    </g>

    <!-- Final State inside composite -->
    <line x1="235" y1="475" x2="310" y2="475" class="line" />
    <circle cx="330" cy="475" r="10" stroke="#0f172a" stroke-width="1.5" fill="none" />
    <circle cx="330" cy="475" r="5" fill="#0f172a" />
    <text x="350" y="480" class="action-text">會話就緒 [*]</text>
  </g>
</svg>
"""

def generate_svg_diagnosis():
    # 7-4-2 影像上傳與雙模型並行診斷 狀態圖
    return """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1150 720" width="1150" height="720">
  <defs>
    <style>
      .title { font-family: 'Microsoft JhengHei', sans-serif; font-size: 20px; font-weight: bold; fill: #0f172a; }
      .group-title { font-family: 'Microsoft JhengHei', sans-serif; font-size: 13px; font-weight: bold; fill: #1e293b; }
      .state-name { font-family: 'Microsoft JhengHei', sans-serif; font-size: 12px; font-weight: bold; fill: #0f172a; text-anchor: middle; }
      .action-text { font-family: 'Microsoft JhengHei', sans-serif; font-size: 10px; fill: #475569; }
      .transition-text { font-family: 'Microsoft JhengHei', sans-serif; font-size: 10px; fill: #1d4ed8; font-weight: 500; }
      .guard-text { font-family: 'Microsoft JhengHei', sans-serif; font-size: 9px; fill: #b91c1c; font-style: italic; }
      
      .composite-bg { fill: #f8fafc; stroke: #94a3b8; stroke-width: 1.5; stroke-dasharray: 6,4; rx: 8; ry: 8; }
      .composite-header { fill: #e2e8f0; stroke: #94a3b8; stroke-width: 1.5; }
      
      .state-box { fill: #ffffff; stroke: #2563eb; stroke-width: 1.5; rx: 6; ry: 6; filter: drop-shadow(0 2px 4px rgba(0,0,0,0.06)); }
      .state-header { fill: #eff6ff; stroke: #2563eb; stroke-width: 1.5; }
      
      .ai-box { fill: #f0fdf4; stroke: #16a34a; stroke-width: 1.5; rx: 6; ry: 6; }
      .ai-header { fill: #dcfce7; stroke: #16a34a; stroke-width: 1.5; }
      
      .line { stroke: #334155; stroke-width: 1.3; fill: none; marker-end: url(#arrow); }
      .fork-join { stroke: #0f172a; stroke-width: 4; fill: none; }
    </style>
    <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M 0 1 L 10 5 L 0 9 z" fill="#334155" />
    </marker>
  </defs>

  <rect width="100%" height="100%" fill="#ffffff" />
  <text x="575" y="32" class="title" text-anchor="middle">圖 7-4-2 影像上傳與雙模型並行診斷 狀態圖 (State Diagram)</text>

  <!-- Initial State -->
  <circle cx="40" cy="120" r="8" fill="#0f172a" />
  <line x1="48" y1="120" x2="80" y2="120" class="line" />

  <!-- ================= CLIENT SUB-PROCESS ================= -->
  <g transform="translate(85, 60)">
    <rect width="250" height="620" class="composite-bg" />
    <path d="M 0 8 Q 0 0 8 0 L 242 0 Q 250 0 250 8 L 250 30 L 0 30 Z" class="composite-header" />
    <text x="15" y="20" class="group-title">客戶端拍照與傳輸狀態 (Client)</text>

    <!-- State 1: 待選圖 -->
    <g transform="translate(20, 50)">
      <rect width="210" height="70" class="state-box" />
      <path d="M 0 6 Q 0 0 6 0 L 204 0 Q 210 0 210 6 L 210 24 L 0 24 Z" class="state-header" />
      <text x="105" y="17" class="state-name">待拍攝/選圖 (Idle_Ready)</text>
      <text x="10" y="42" class="action-text">entry / 啟動 CameraX 或打開相簿</text>
      <text x="10" y="58" class="action-text">do / 拍照或選取植物葉片照片</text>
    </g>

    <line x1="125" y1="120" x2="125" y2="175" class="line" />
    <text x="130" y="150" class="transition-text">選取照片完畢</text>

    <!-- State 2: 影像前處理中 -->
    <g transform="translate(20, 175)">
      <rect width="210" height="75" class="state-box" />
      <path d="M 0 6 Q 0 0 6 0 L 204 0 Q 210 0 210 6 L 210 24 L 0 24 Z" class="state-header" />
      <text x="105" y="17" class="state-name">影像預處理 (Preprocessing)</text>
      <text x="10" y="42" class="action-text">do / 本機壓縮至最適解析度</text>
      <text x="10" y="56" class="action-text">do / EXIF 旋轉向校正</text>
      <text x="10" y="70" class="action-text">do / 轉為 JPEG 二進位流</text>
    </g>

    <line x1="125" y1="250" x2="125" y2="305" class="line" />
    <text x="130" y="280" class="transition-text">點擊開始診斷</text>

    <!-- State 3: 上傳傳輸中 -->
    <g transform="translate(20, 305)">
      <rect width="210" height="75" class="state-box" />
      <path d="M 0 6 Q 0 0 6 0 L 204 0 Q 210 0 210 6 L 210 24 L 0 24 Z" class="state-header" />
      <text x="105" y="17" class="state-name">上傳傳輸中 (Uploading)</text>
      <text x="10" y="42" class="action-text">entry / 注入 Bearer JWT Token</text>
      <text x="10" y="56" class="action-text">do / Multipart/form-data 傳輸</text>
      <text x="10" y="70" class="action-text">do / POST /api/v1/predict</text>
    </g>

    <!-- State 7: 診斷結果呈現中 -->
    <g transform="translate(20, 470)">
      <rect width="210" height="95" class="state-box" />
      <path d="M 0 6 Q 0 0 6 0 L 204 0 Q 210 0 210 6 L 210 24 L 0 24 Z" class="state-header" />
      <text x="105" y="17" class="state-name">結果展示 (Result_Displayed)</text>
      <text x="10" y="42" class="action-text">entry / 渲染病害診斷卡片</text>
      <text x="10" y="56" class="action-text">do / 顯示病害名、置信度、處置方針</text>
      <text x="10" y="70" class="action-text">do / 保存 prediction_id 於記憶體</text>
      <text x="10" y="85" class="action-text">exit / 導向儲存或糾錯</text>
    </g>

    <line x1="125" y1="565" x2="125" y2="595" class="line" />
    <circle cx="125" cy="605" r="9" stroke="#0f172a" stroke-width="1.5" fill="none" />
    <circle cx="125" cy="605" r="5" fill="#0f172a" />
  </g>

  <!-- Client to Server Transition -->
  <path d="M 295 342 L 380 342 L 380 120 L 415 120" class="line" />
  <text x="350" y="240" class="transition-text" transform="rotate(-90, 350, 240)">接收影像檔案串流</text>

  <!-- ================= SERVER SUBSYSTEM ================= -->
  <g transform="translate(420, 60)">
    <rect width="690" height="620" class="composite-bg" />
    <path d="M 0 8 Q 0 0 8 0 L 682 0 Q 690 0 690 8 L 690 30 L 0 30 Z" class="composite-header" />
    <text x="15" y="20" class="group-title">伺服器端雙模型並行推論與決策仲裁狀態 (Backend Inference Engine)</text>

    <!-- State 4: 暫存影像並分配唯一 ID -->
    <g transform="translate(200, 45)">
      <rect width="280" height="65" class="state-box" />
      <path d="M 0 6 Q 0 0 6 0 L 274 0 Q 280 0 280 6 L 280 24 L 0 24 Z" class="state-header" />
      <text x="140" y="17" class="state-name">暫存與分配 ID (Cached_With_ID)</text>
      <text x="10" y="42" class="action-text">do / 影像寫入暫存目錄 static/temp/</text>
      <text x="10" y="56" class="action-text">do / 生成 UUID prediction_id，存入 10 分鐘快取</text>
    </g>

    <!-- Transition to Fork Bar -->
    <line x1="340" y1="110" x2="340" y2="140" class="line" />
    <text x="348" y="128" class="transition-text">非同步並行派發</text>

    <!-- Fork Bar -->
    <line x1="70" y1="140" x2="610" y2="140" class="fork-join" />

    <!-- Branch A: Gemini 2.5 Flash -->
    <line x1="120" y1="140" x2="120" y2="175" class="line" />
    <g transform="translate(20, 175)">
      <rect width="200" height="90" class="ai-box" />
      <path d="M 0 6 Q 0 0 6 0 L 194 0 Q 200 0 200 6 L 200 24 L 0 24 Z" class="ai-header" />
      <text x="100" y="17" class="state-name" fill="#15803d">Gemini 2.5 Flash 雲端分析</text>
      <text x="8" y="42" class="action-text">do / google-genai 官方 SDK</text>
      <text x="8" y="56" class="action-text">do / 多模態病理特徵描述</text>
      <text x="8" y="70" class="action-text">do / 全局病徵辨識與語意理解</text>
      <text x="8" y="84" class="action-text">do / JSON Schema 結構化輸出</text>
    </g>

    <!-- Branch B: Local ConvNet -->
    <line x1="340" y1="140" x2="340" y2="175" class="line" />
    <g transform="translate(240, 175)">
      <rect width="200" height="90" class="ai-box" />
      <path d="M 0 6 Q 0 0 6 0 L 194 0 Q 200 0 200 6 L 200 24 L 0 24 Z" class="ai-header" />
      <text x="100" y="17" class="state-name" fill="#15803d">本地自訓 ConvNet 微觀分析</text>
      <text x="8" y="42" class="action-text">do / PyTorch 卷積神經網路</text>
      <text x="8" y="56" class="action-text">do / 38 種特定作物病害分類</text>
      <text x="8" y="70" class="action-text">do / 局部病斑紋理特徵擷取</text>
      <text x="8" y="84" class="action-text">do / 零雲端託管費用、即時推論</text>
    </g>

    <!-- Branch C: FAISS RAG -->
    <line x1="560" y1="140" x2="560" y2="175" class="line" />
    <g transform="translate(460, 175)">
      <rect width="210" height="90" class="ai-box" />
      <path d="M 0 6 Q 0 0 6 0 L 204 0 Q 210 0 210 6 L 210 24 L 0 24 Z" class="ai-header" />
      <text x="105" y="17" class="state-name" fill="#15803d">FAISS 向量檢索 (RAG)</text>
      <text x="8" y="42" class="action-text">do / 農業部開放病害知識庫檢索</text>
      <text x="8" y="56" class="action-text">do / 語意相似度校驗防幻覺</text>
      <text x="8" y="70" class="action-text">do / 提取權威用藥與處置建議</text>
      <text x="8" y="84" class="action-text">do / 毫秒級高維向量索引查詢</text>
    </g>

    <!-- Join Bar -->
    <line x1="120" y1="265" x2="120" y2="300" class="line" />
    <line x1="340" y1="265" x2="340" y2="300" class="line" />
    <line x1="560" y1="265" x2="560" y2="300" class="line" />
    <line x1="70" y1="300" x2="610" y2="300" class="fork-join" />

    <!-- Transition from Join to Arbitration -->
    <line x1="340" y1="300" x2="340" y2="335" class="line" />
    <text x="348" y="322" class="transition-text">三路推論匯流</text>

    <!-- State 5: 決策仲裁與防幻覺過濾 -->
    <g transform="translate(180, 335)">
      <rect width="320" height="100" class="state-box" />
      <path d="M 0 6 Q 0 0 6 0 L 314 0 Q 320 0 320 6 L 320 24 L 0 24 Z" class="state-header" />
      <text x="160" y="17" class="state-name">多模型決策仲裁 (Arbitration)</text>
      <text x="10" y="42" class="action-text">do / 雙模型標籤一致性交叉核對</text>
      <text x="10" y="56" class="action-text">do / 廣域描述與微觀特徵互補加權</text>
      <text x="10" y="70" class="action-text">do / 嚴格執行 70% 信心度閾值檢查</text>
      <text x="10" y="84" class="guard-text">[信心度 &lt; 70%] 標記為需人工專家覆核</text>
      <text x="10" y="96" class="guard-text">[信心度 &gt;= 70%] 判定為高信度有效診斷</text>
    </g>

    <line x1="340" y1="435" x2="340" y2="480" class="line" />
    <text x="348" y="460" class="transition-text">生成結構化回應</text>

    <!-- State 6: 診斷結果暫存就緒 -->
    <g transform="translate(180, 480)">
      <rect width="320" height="80" class="state-box" />
      <path d="M 0 6 Q 0 0 6 0 L 314 0 Q 320 0 320 6 L 320 24 L 0 24 Z" class="state-header" />
      <text x="160" y="17" class="state-name">結果暫存就緒 (Diagnosis_Ready)</text>
      <text x="10" y="42" class="action-text">do / 組裝 DiagnosisResponse (作物、病名、方針)</text>
      <text x="10" y="56" class="action-text">do / 暫存 10 分鐘等待使用者確認儲存</text>
      <text x="10" y="70" class="action-text">do / HTTP 200 回傳 JSON 響應至客戶端</text>
    </g>
  </g>

  <!-- Server to Client Response Transition -->
  <path d="M 600 620 L 600 650 L 315 650 L 315 520 L 295 520" class="line" />
  <text x="440" y="643" class="transition-text" text-anchor="middle">HTTP 200 返回 JSON 診斷卡片數據</text>
</svg>
"""

def generate_svg_save_diary():
    # 7-4-3 儲存診斷紀錄 狀態圖
    return """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1100 680" width="1100" height="680">
  <defs>
    <style>
      .title { font-family: 'Microsoft JhengHei', sans-serif; font-size: 20px; font-weight: bold; fill: #0f172a; }
      .group-title { font-family: 'Microsoft JhengHei', sans-serif; font-size: 13px; font-weight: bold; fill: #1e293b; }
      .state-name { font-family: 'Microsoft JhengHei', sans-serif; font-size: 12px; font-weight: bold; fill: #0f172a; text-anchor: middle; }
      .action-text { font-family: 'Microsoft JhengHei', sans-serif; font-size: 10px; fill: #475569; }
      .transition-text { font-family: 'Microsoft JhengHei', sans-serif; font-size: 10px; fill: #1d4ed8; font-weight: 500; }
      .guard-text { font-family: 'Microsoft JhengHei', sans-serif; font-size: 9px; fill: #b91c1c; font-style: italic; }
      
      .composite-bg { fill: #f8fafc; stroke: #94a3b8; stroke-width: 1.5; stroke-dasharray: 6,4; rx: 8; ry: 8; }
      .composite-header { fill: #e2e8f0; stroke: #94a3b8; stroke-width: 1.5; }
      
      .state-box { fill: #ffffff; stroke: #2563eb; stroke-width: 1.5; rx: 6; ry: 6; filter: drop-shadow(0 2px 4px rgba(0,0,0,0.06)); }
      .state-header { fill: #eff6ff; stroke: #2563eb; stroke-width: 1.5; }
      
      .error-state-box { fill: #fef2f2; stroke: #dc2626; stroke-width: 1.5; rx: 6; ry: 6; }
      .error-state-header { fill: #fee2e2; stroke: #dc2626; stroke-width: 1.5; }
      
      .line { stroke: #334155; stroke-width: 1.3; fill: none; marker-end: url(#arrow); }
      .line-back { stroke: #64748b; stroke-width: 1.2; stroke-dasharray: 4,3; fill: none; marker-end: url(#arrow); }
    </style>
    <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M 0 1 L 10 5 L 0 9 z" fill="#334155" />
    </marker>
  </defs>

  <rect width="100%" height="100%" fill="#ffffff" />
  <text x="550" y="32" class="title" text-anchor="middle">圖 7-4-3 診斷紀錄確認與備忘筆記儲存 狀態圖 (State Diagram)</text>

  <!-- Initial State -->
  <circle cx="50" cy="120" r="8" fill="#0f172a" />
  <line x1="58" y1="120" x2="90" y2="120" class="line" />

  <!-- ================= CLIENT INTERACTION ================= -->
  <g transform="translate(95, 60)">
    <rect width="360" height="580" class="composite-bg" />
    <path d="M 0 8 Q 0 0 8 0 L 352 0 Q 360 0 360 8 L 360 30 L 0 30 Z" class="composite-header" />
    <text x="15" y="20" class="group-title">客戶端檢閱與備忘編輯狀態 (Client Review &amp; Note)</text>

    <!-- State 1: 檢閱診斷結論 -->
    <g transform="translate(25, 50)">
      <rect width="310" height="70" class="state-box" />
      <path d="M 0 6 Q 0 0 6 0 L 304 0 Q 310 0 310 6 L 310 24 L 0 24 Z" class="state-header" />
      <text x="155" y="17" class="state-name">檢閱診斷結論 (Reviewing_Diagnosis)</text>
      <text x="10" y="42" class="action-text">entry / 顯示 AI 推論病害名稱與信心度指標</text>
      <text x="10" y="58" class="action-text">do / 檢視建議之防治方式（化學藥劑與有機方針）</text>
    </g>

    <line x1="180" y1="120" x2="180" y2="175" class="line" />
    <text x="185" y="150" class="transition-text">點擊填寫備忘或直接儲存</text>

    <!-- State 2: 編輯個人備忘筆記 -->
    <g transform="translate(25, 175)">
      <rect width="310" height="80" class="state-box" />
      <path d="M 0 6 Q 0 0 6 0 L 304 0 Q 310 0 310 6 L 310 24 L 0 24 Z" class="state-header" />
      <text x="155" y="17" class="state-name">編輯個人備忘 (Editing_User_Note)</text>
      <text x="10" y="42" class="action-text">entry / 展開個人筆記輸入區域 (user_note)</text>
      <text x="10" y="56" class="action-text">do / 輸入自定義備忘、栽種位置、施藥心得</text>
      <text x="10" y="70" class="action-text">exit / 打包 prediction_id 與 user_note</text>
    </g>

    <line x1="180" y1="255" x2="180" y2="310" class="line" />
    <text x="185" y="285" class="transition-text">點擊「確認儲存日誌」</text>

    <!-- State 3: 提交儲存請求中 -->
    <g transform="translate(25, 310)">
      <rect width="310" height="75" class="state-box" />
      <path d="M 0 6 Q 0 0 6 0 L 304 0 Q 310 0 310 6 L 310 24 L 0 24 Z" class="state-header" />
      <text x="155" y="17" class="state-name">提交儲存請求 (Submitting_Confirm)</text>
      <text x="10" y="42" class="action-text">entry / 顯示儲存進度對話框</text>
      <text x="10" y="56" class="action-text">do / 發送 POST /api/v1/diaries/confirm</text>
      <text x="10" y="70" class="action-text">do / 攜帶 Bearer JWT 與診斷關聯資料</text>
    </g>

    <!-- State 7: 本機日誌儲存成功 -->
    <g transform="translate(25, 455)">
      <rect width="310" height="80" class="state-box" />
      <path d="M 0 6 Q 0 0 6 0 L 304 0 Q 310 0 310 6 L 310 24 L 0 24 Z" class="state-header" />
      <text x="155" y="17" class="state-name">日誌儲存成功 (Diary_Saved)</text>
      <text x="10" y="42" class="action-text">entry / 提示「診斷紀錄已儲存至個人日誌」</text>
      <text x="10" y="56" class="action-text">do / 本機歷史日誌列表即時刷新快取</text>
      <text x="10" y="70" class="action-text">exit / 自動跳轉歷史紀錄詳細頁</text>
    </g>

    <line x1="180" y1="535" x2="180" y2="570" class="line" />
    <circle cx="180" cy="580" r="9" stroke="#0f172a" stroke-width="1.5" fill="none" />
    <circle cx="180" cy="580" r="5" fill="#0f172a" />
  </g>

  <!-- Client to Server Transition -->
  <path d="M 405 347 L 510 347 L 510 120 L 545 120" class="line" />
  <text x="480" y="240" class="transition-text" transform="rotate(-90, 480, 240)">發送確認請求</text>

  <!-- ================= SERVER PERSISTENCE ================= -->
  <g transform="translate(550, 60)">
    <rect width="500" height="580" class="composite-bg" />
    <path d="M 0 8 Q 0 0 8 0 L 492 0 Q 500 0 500 8 L 500 30 L 0 30 Z" class="composite-header" />
    <text x="15" y="20" class="group-title">伺服器端資料持久化管線 (Database Persistence Pipeline)</text>

    <!-- State 4: 檢驗 prediction_id -->
    <g transform="translate(30, 50)">
      <rect width="260" height="75" class="state-box" />
      <path d="M 0 6 Q 0 0 6 0 L 254 0 Q 260 0 260 6 L 260 24 L 0 24 Z" class="state-header" />
      <text x="130" y="17" class="state-name">快取有效性核對 (Cache_Check)</text>
      <text x="10" y="42" class="action-text">do / 查詢快取中是否存在 prediction_id</text>
      <text x="10" y="56" class="action-text">do / 驗證請求者 user_id 身分所有權</text>
      <text x="10" y="70" class="action-text">do / 防止重複提交寫入</text>
    </g>

    <!-- Transition: Expired / Invalid -->
    <line x1="290" y1="87" x2="350" y2="87" class="line" />
    <text x="320" y="80" class="guard-text" text-anchor="middle">[快取已過期]</text>

    <!-- State: 錯誤回傳 -->
    <g transform="translate(350, 55)">
      <rect width="130" height="60" class="error-state-box" />
      <path d="M 0 6 Q 0 0 6 0 L 124 0 Q 130 0 130 6 L 130 22 L 0 22 Z" class="error-state-header" />
      <text x="65" y="16" class="state-name" fill="#991b1b">快取失效 (404)</text>
      <text x="8" y="38" class="action-text" fill="#b91c1c">回傳逾時錯誤提示</text>
      <text x="8" y="50" class="action-text" fill="#b91c1c">請重新拍照診斷</text>
    </g>

    <line x1="160" y1="125" x2="160" y2="180" class="line" />
    <text x="165" y="155" class="transition-text">[快取有效，取出影像與結果]</text>

    <!-- State 5: 移轉影像至永久儲存 -->
    <g transform="translate(30, 180)">
      <rect width="260" height="75" class="state-box" />
      <path d="M 0 6 Q 0 0 6 0 L 254 0 Q 260 0 260 6 L 260 24 L 0 24 Z" class="state-header" />
      <text x="130" y="17" class="state-name">移轉檔案 (Persist_Image_File)</text>
      <text x="10" y="42" class="action-text">do / 將暫存圖片移至 static/uploads/diaries/</text>
      <text x="10" y="56" class="action-text">do / 依 user_id 與日期建立子目錄</text>
      <text x="10" y="70" class="action-text">do / 生成永久相對訪問路徑</text>
    </g>

    <line x1="160" y1="255" x2="160" y2="310" class="line" />
    <text x="165" y="285" class="transition-text">建立持久化實體</text>

    <!-- State 6: 寫入 MySQL plant_diary -->
    <g transform="translate(30, 310)">
      <rect width="320" height="95" class="state-box" />
      <path d="M 0 6 Q 0 0 6 0 L 314 0 Q 320 0 320 6 L 320 24 L 0 24 Z" class="state-header" />
      <text x="160" y="17" class="state-name">寫入資料庫實體 (Write_MySQL_Diary)</text>
      <text x="10" y="42" class="action-text">do / 實例化 PlantDiary (user_id, crop_id, disease_id)</text>
      <text x="10" y="56" class="action-text">do / 存入使用者備忘筆記 (user_note)</text>
      <text x="10" y="70" class="action-text">do / 儲存影像 URL、信心度數值與診斷時間戳記</text>
      <text x="10" y="85" class="action-text">do / SQLAlchemy db.session.commit()</text>
    </g>

    <line x1="160" y1="405" x2="160" y2="455" class="line" />
    <text x="165" y="432" class="transition-text">寫入成功 / 清除暫存</text>

    <!-- State 7: 清理暫存快取 -->
    <g transform="translate(30, 455)">
      <rect width="260" height="65" class="state-box" />
      <path d="M 0 6 Q 0 0 6 0 L 254 0 Q 260 0 260 6 L 260 24 L 0 24 Z" class="state-header" />
      <text x="130" y="17" class="state-name">清理快取 (Purge_Cache)</text>
      <text x="10" y="42" class="action-text">do / 自快取註銷 prediction_id</text>
      <text x="10" y="56" class="action-text">do / 回傳 HTTP 201 Created 與日誌資料</text>
    </g>
  </g>

  <!-- Server to Client Response Transition -->
  <path d="M 580 520 L 520 520 L 520 495 L 405 495" class="line" />
  <text x="465" y="488" class="transition-text" text-anchor="middle">HTTP 201 回傳 PlantDiaryDTO</text>
</svg>
"""

def generate_svg_history():
    # 7-4-4 查看歷史紀錄與備忘編輯 狀態圖
    return """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1100 680" width="1100" height="680">
  <defs>
    <style>
      .title { font-family: 'Microsoft JhengHei', sans-serif; font-size: 20px; font-weight: bold; fill: #0f172a; }
      .group-title { font-family: 'Microsoft JhengHei', sans-serif; font-size: 13px; font-weight: bold; fill: #1e293b; }
      .state-name { font-family: 'Microsoft JhengHei', sans-serif; font-size: 12px; font-weight: bold; fill: #0f172a; text-anchor: middle; }
      .action-text { font-family: 'Microsoft JhengHei', sans-serif; font-size: 10px; fill: #475569; }
      .transition-text { font-family: 'Microsoft JhengHei', sans-serif; font-size: 10px; fill: #1d4ed8; font-weight: 500; }
      .guard-text { font-family: 'Microsoft JhengHei', sans-serif; font-size: 9px; fill: #b91c1c; font-style: italic; }
      
      .composite-bg { fill: #f8fafc; stroke: #94a3b8; stroke-width: 1.5; stroke-dasharray: 6,4; rx: 8; ry: 8; }
      .composite-header { fill: #e2e8f0; stroke: #94a3b8; stroke-width: 1.5; }
      
      .state-box { fill: #ffffff; stroke: #2563eb; stroke-width: 1.5; rx: 6; ry: 6; filter: drop-shadow(0 2px 4px rgba(0,0,0,0.06)); }
      .state-header { fill: #eff6ff; stroke: #2563eb; stroke-width: 1.5; }
      
      .edit-box { fill: #fffbeb; stroke: #d97706; stroke-width: 1.5; rx: 6; ry: 6; }
      .edit-header { fill: #fef3c7; stroke: #d97706; stroke-width: 1.5; }
      
      .feedback-box { fill: #f5f3ff; stroke: #7c3aed; stroke-width: 1.5; rx: 6; ry: 6; }
      .feedback-header { fill: #ede9fe; stroke: #7c3aed; stroke-width: 1.5; }
      
      .line { stroke: #334155; stroke-width: 1.3; fill: none; marker-end: url(#arrow); }
      .line-back { stroke: #64748b; stroke-width: 1.2; stroke-dasharray: 4,3; fill: none; marker-end: url(#arrow); }
    </style>
    <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M 0 1 L 10 5 L 0 9 z" fill="#334155" />
    </marker>
  </defs>

  <rect width="100%" height="100%" fill="#ffffff" />
  <text x="550" y="32" class="title" text-anchor="middle">圖 7-4-4 查看歷史紀錄與備忘編輯 狀態圖 (State Diagram)</text>

  <!-- Initial State -->
  <circle cx="50" cy="120" r="8" fill="#0f172a" />
  <line x1="58" y1="120" x2="95" y2="120" class="line" />

  <!-- ================= MAIN FLOW: LIST & DETAIL ================= -->
  <g transform="translate(100, 60)">
    <rect width="440" height="580" class="composite-bg" />
    <path d="M 0 8 Q 0 0 8 0 L 432 0 Q 440 0 440 8 L 440 30 L 0 30 Z" class="composite-header" />
    <text x="15" y="20" class="group-title">主歷程檢視狀態 (Browsing History &amp; Detail)</text>

    <!-- State 1: 請求日誌清單 -->
    <g transform="translate(30, 50)">
      <rect width="240" height="75" class="state-box" />
      <path d="M 0 6 Q 0 0 6 0 L 234 0 Q 240 0 240 6 L 240 24 L 0 24 Z" class="state-header" />
      <text x="120" y="17" class="state-name">加載日誌列表 (Loading_Diaries)</text>
      <text x="10" y="42" class="action-text">entry / 發送 GET /api/v1/diaries (帶 JWT)</text>
      <text x="10" y="56" class="action-text">do / 後端查詢該 user_id 所有 plant_diary</text>
      <text x="10" y="70" class="action-text">do / 按診斷建立時間降冪排序</text>
    </g>

    <line x1="150" y1="125" x2="150" y2="185" class="line" />
    <text x="155" y="160" class="transition-text">清單載入完畢</text>

    <!-- State 2: 歷史列表呈現中 -->
    <g transform="translate(30, 185)">
      <rect width="240" height="85" class="state-box" />
      <path d="M 0 6 Q 0 0 6 0 L 234 0 Q 240 0 240 6 L 240 24 L 0 24 Z" class="state-header" />
      <text x="120" y="17" class="state-name">日誌清單展示 (Diary_List_Active)</text>
      <text x="10" y="42" class="action-text">entry / RecyclerView 渲染縮圖與病害摘要</text>
      <text x="10" y="56" class="action-text">do / 呈現診斷日期、置信度徽章、筆記摘要</text>
      <text x="10" y="70" class="action-text">do / 支援下拉更新與關鍵字篩選</text>
      <text x="10" y="82" class="action-text">exit / 選取特定項目進入詳情</text>
    </g>

    <line x1="150" y1="270" x2="150" y2="330" class="line" />
    <text x="155" y="305" class="transition-text">點擊單筆日誌項目</text>

    <!-- State 3: 日誌詳情檢閱中 -->
    <g transform="translate(30, 330)">
      <rect width="280" height="100" class="state-box" />
      <path d="M 0 6 Q 0 0 6 0 L 274 0 Q 280 0 280 6 L 280 24 L 0 24 Z" class="state-header" />
      <text x="140" y="17" class="state-name">檢視日誌詳情 (Viewing_Detail)</text>
      <text x="10" y="42" class="action-text">entry / 啟動 HistoryDetailActivity</text>
      <text x="10" y="56" class="action-text">do / 展示高解析原始患病葉片照片</text>
      <text x="10" y="70" class="action-text">do / 呈現完整診斷結論、化學/有機防治處方</text>
      <text x="10" y="84" class="action-text">do / 顯示個人備忘筆記區塊 (user_note)</text>
      <text x="10" y="96" class="action-text">do / 提供「編輯筆記」與「糾錯反饋」按鈕</text>
    </g>

    <!-- Final State -->
    <line x1="150" y1="430" x2="150" y2="490" class="line" />
    <text x="155" y="465" class="transition-text">離開歷史頁</text>
    <circle cx="150" cy="510" r="9" stroke="#0f172a" stroke-width="1.5" fill="none" />
    <circle cx="150" cy="510" r="5" fill="#0f172a" />
  </g>

  <!-- ================= BRANCH ACTIONS ================= -->
  <!-- Branch 1: Edit Note -->
  <path d="M 410 380 L 590 380 L 590 150 L 630 150" class="line" />
  <text x="500" y="260" class="transition-text" transform="rotate(-90, 500, 260)">點擊「編輯備忘筆記」(UC-08)</text>

  <g transform="translate(630, 60)">
    <rect width="430" height="260" class="composite-bg" />
    <path d="M 0 8 Q 0 0 8 0 L 422 0 Q 430 0 430 8 L 430 30 L 0 30 Z" class="composite-header" fill="#fef3c7" />
    <text x="15" y="20" class="group-title" fill="#92400e">分支狀態 A：編輯個人備忘筆記 (UC-08)</text>

    <!-- State 4: 編輯備忘對話框 -->
    <g transform="translate(20, 45)">
      <rect width="390" height="75" class="edit-box" />
      <path d="M 0 6 Q 0 0 6 0 L 384 0 Q 390 0 390 6 L 390 24 L 0 24 Z" class="edit-header" />
      <text x="195" y="17" class="state-name" fill="#92400e">備忘編輯狀態 (Editing_User_Note)</text>
      <text x="10" y="42" class="action-text">entry / 彈出筆記對話框，預載既有 user_note</text>
      <text x="10" y="56" class="action-text">do / 使用者鍵入最新照護進展、施藥時間心得</text>
      <text x="10" y="70" class="action-text">exit / 點擊「儲存筆記」發送 PATCH /api/v1/diaries/{id}/note</text>
    </g>

    <line x1="215" y1="120" x2="215" y2="155" class="line" />

    <!-- State 5: 資料庫持久化與即時刷新 -->
    <g transform="translate(20, 155)">
      <rect width="390" height="75" class="edit-box" />
      <path d="M 0 6 Q 0 0 6 0 L 384 0 Q 390 0 390 6 L 390 24 L 0 24 Z" class="edit-header" />
      <text x="195" y="17" class="state-name" fill="#92400e">筆記寫入與同步 (Note_Updated)</text>
      <text x="10" y="42" class="action-text">do / 後端更新 MySQL plant_diary.user_note 欄位</text>
      <text x="10" y="56" class="action-text">do / 回傳 200 OK，即時更新詳情頁備忘文字</text>
      <text x="10" y="70" class="action-text">exit / 提示「筆記儲存成功」，關閉對話框</text>
    </g>
  </g>

  <!-- Loop back from Note to Detail -->
  <path d="M 630 250 L 560 250 L 560 400 L 410 400" class="line-back" />
  <text x="520" y="325" class="transition-text" text-anchor="middle">返回詳情頁</text>

  <!-- Branch 2: Submit Feedback -->
  <path d="M 410 415 L 590 415 L 590 470 L 630 470" class="line" />
  <text x="500" y="450" class="transition-text">點擊「反饋糾錯」(UC-13)</text>

  <g transform="translate(630, 360)">
    <rect width="430" height="280" class="composite-bg" />
    <path d="M 0 8 Q 0 0 8 0 L 422 0 Q 430 0 430 8 L 430 30 L 0 30 Z" class="composite-header" fill="#ede9fe" />
    <text x="15" y="20" class="group-title" fill="#5b21b6">分支狀態 B：提交診斷反饋與糾錯 (UC-13)</text>

    <!-- State 6: 填寫糾錯資訊 -->
    <g transform="translate(20, 45)">
      <rect width="390" height="80" class="feedback-box" />
      <path d="M 0 6 Q 0 0 6 0 L 384 0 Q 390 0 390 6 L 390 24 L 0 24 Z" class="feedback-header" />
      <text x="195" y="17" class="state-name" fill="#5b21b6">填寫糾錯反饋 (Filling_Feedback_Modal)</text>
      <text x="10" y="42" class="action-text">entry / 彈出糾錯表單，顯示 AI 原始判定</text>
      <text x="10" y="56" class="action-text">do / 勾選錯誤類別 (作物誤判 / 病害誤判)</text>
      <text x="10" y="70" class="action-text">do / 鍵入使用者認為正確之作物名與病害名</text>
    </g>

    <line x1="215" y1="125" x2="215" y2="160" class="line" />

    <!-- State 7: 送交 diagnosis_feedback -->
    <g transform="translate(20, 160)">
      <rect width="390" height="95" class="feedback-box" />
      <path d="M 0 6 Q 0 0 6 0 L 384 0 Q 390 0 390 6 L 390 24 L 0 24 Z" class="feedback-header" />
      <text x="195" y="17" class="state-name" fill="#5b21b6">反饋持久化 (Feedback_Persisted)</text>
      <text x="10" y="42" class="action-text">do / 發送 POST /api/v1/feedback</text>
      <text x="10" y="56" class="action-text">do / 寫入 MySQL diagnosis_feedback 表格</text>
      <text x="10" y="70" class="action-text">do / 影像歸檔至 feedback_uploads 資料夾</text>
      <text x="10" y="84" class="action-text">exit / 作為專家審核與本地 ConvNet 模型微調樣本</text>
    </g>
  </g>

  <!-- Loop back from Feedback to Detail -->
  <path d="M 630 580 L 560 580 L 560 425 L 410 425" class="line-back" />
  <text x="520" y="510" class="transition-text" text-anchor="middle">返回詳情頁</text>
</svg>
"""

def generate_svg_admin():
    # 7-4-5 檢視儀表板與日誌管理 狀態圖
    return """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1150 700" width="1150" height="700">
  <defs>
    <style>
      .title { font-family: 'Microsoft JhengHei', sans-serif; font-size: 20px; font-weight: bold; fill: #0f172a; }
      .group-title { font-family: 'Microsoft JhengHei', sans-serif; font-size: 13px; font-weight: bold; fill: #1e293b; }
      .state-name { font-family: 'Microsoft JhengHei', sans-serif; font-size: 12px; font-weight: bold; fill: #0f172a; text-anchor: middle; }
      .action-text { font-family: 'Microsoft JhengHei', sans-serif; font-size: 10px; fill: #475569; }
      .transition-text { font-family: 'Microsoft JhengHei', sans-serif; font-size: 10px; fill: #1d4ed8; font-weight: 500; }
      .guard-text { font-family: 'Microsoft JhengHei', sans-serif; font-size: 9px; fill: #b91c1c; font-style: italic; }
      
      .composite-bg { fill: #f8fafc; stroke: #94a3b8; stroke-width: 1.5; stroke-dasharray: 6,4; rx: 8; ry: 8; }
      .composite-header { fill: #e2e8f0; stroke: #94a3b8; stroke-width: 1.5; }
      
      .state-box { fill: #ffffff; stroke: #2563eb; stroke-width: 1.5; rx: 6; ry: 6; filter: drop-shadow(0 2px 4px rgba(0,0,0,0.06)); }
      .state-header { fill: #eff6ff; stroke: #2563eb; stroke-width: 1.5; }
      
      .danger-box { fill: #fef2f2; stroke: #dc2626; stroke-width: 1.5; rx: 6; ry: 6; }
      .danger-header { fill: #fee2e2; stroke: #dc2626; stroke-width: 1.5; }
      
      .ai-box { fill: #f0fdf4; stroke: #16a34a; stroke-width: 1.5; rx: 6; ry: 6; }
      .ai-header { fill: #dcfce7; stroke: #16a34a; stroke-width: 1.5; }
      
      .line { stroke: #334155; stroke-width: 1.3; fill: none; marker-end: url(#arrow); }
      .line-back { stroke: #64748b; stroke-width: 1.2; stroke-dasharray: 4,3; fill: none; marker-end: url(#arrow); }
    </style>
    <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M 0 1 L 10 5 L 0 9 z" fill="#334155" />
    </marker>
  </defs>

  <rect width="100%" height="100%" fill="#ffffff" />
  <text x="575" y="32" class="title" text-anchor="middle">圖 7-4-5 檢視儀表板與日誌管理 狀態圖 (State Diagram)</text>

  <!-- Initial State -->
  <circle cx="50" cy="120" r="8" fill="#0f172a" />
  <line x1="58" y1="120" x2="95" y2="120" class="line" />

  <!-- ================= COMPOSITE 1: DASHBOARD OVERVIEW ================= -->
  <g transform="translate(100, 60)">
    <rect width="310" height="600" class="composite-bg" />
    <path d="M 0 8 Q 0 0 8 0 L 302 0 Q 310 0 310 8 L 310 30 L 0 30 Z" class="composite-header" />
    <text x="15" y="20" class="group-title">管理員儀表板狀態 (Admin Dashboard)</text>

    <!-- State 1: 權限認證 -->
    <g transform="translate(20, 50)">
      <rect width="270" height="75" class="state-box" />
      <path d="M 0 6 Q 0 0 6 0 L 264 0 Q 270 0 270 6 L 270 24 L 0 24 Z" class="state-header" />
      <text x="135" y="17" class="state-name">管理員鑑權 (Admin_Auth)</text>
      <text x="10" y="42" class="action-text">entry / 驗證 JWT Token 具備 Admin 角色</text>
      <text x="10" y="56" class="action-text">guard / [非管理員] 重導向 403 拒絕訪問</text>
      <text x="10" y="70" class="action-text">do / 載入管理者操作控制台</text>
    </g>

    <line x1="155" y1="125" x2="155" y2="185" class="line" />
    <text x="160" y="160" class="transition-text">身分查驗合格</text>

    <!-- State 2: 儀表板總覽 -->
    <g transform="translate(20, 185)">
      <rect width="270" height="100" class="state-box" />
      <path d="M 0 6 Q 0 0 6 0 L 264 0 Q 270 0 270 6 L 270 24 L 0 24 Z" class="state-header" />
      <text x="135" y="17" class="state-name">儀表板總覽態 (Dashboard_Active)</text>
      <text x="10" y="42" class="action-text">entry / 統計全站總診斷次數與植物健康比率</text>
      <text x="10" y="56" class="action-text">do / 渲染病害高發排行榜、用戶活躍度圖表</text>
      <text x="10" y="70" class="action-text">do / 顯示待審核糾錯反饋通知數 (Pending)</text>
      <text x="10" y="84" class="action-text">do / 輪詢 Webcam 監控即時串流與警報狀態</text>
    </g>

    <line x1="155" y1="285" x2="155" y2="350" class="line" />
    <text x="160" y="320" class="transition-text">選擇管理維護模組</text>

    <!-- State 3: 會話維持 -->
    <g transform="translate(20, 350)">
      <rect width="270" height="75" class="state-box" />
      <path d="M 0 6 Q 0 0 6 0 L 264 0 Q 270 0 270 6 L 270 24 L 0 24 Z" class="state-header" />
      <text x="135" y="17" class="state-name">後台會話就緒 (Session_Ready)</text>
      <text x="10" y="42" class="action-text">do / 支援多模組即時切換</text>
      <text x="10" y="56" class="action-text">do / 記錄管理者審計日誌 (Audit Log)</text>
      <text x="10" y="70" class="action-text">exit / 點擊登出銷毀會話</text>
    </g>

    <line x1="155" y1="425" x2="155" y2="480" class="line" />
    <circle cx="155" cy="495" r="9" stroke="#0f172a" stroke-width="1.5" fill="none" />
    <circle cx="155" cy="495" r="5" fill="#0f172a" />
  </g>

  <!-- ================= SUB-PROCESS 1: LOG MANAGEMENT (UC-09) ================= -->
  <path d="M 290 235 L 450 235 L 450 150 L 480 150" class="line" />
  <text x="370" y="195" class="transition-text">進入診斷日誌列表</text>

  <g transform="translate(480, 60)">
    <rect width="630" height="260" class="composite-bg" />
    <path d="M 0 8 Q 0 0 8 0 L 622 0 Q 630 0 630 8 L 630 30 L 0 30 Z" class="composite-header" fill="#fee2e2" />
    <text x="15" y="20" class="group-title" fill="#991b1b">管理功能 1：全站診斷日誌檢視與異常紀錄刪除 (UC-09 專屬權限)</text>

    <!-- State 4: 檢閱全站日誌清單 -->
    <g transform="translate(20, 50)">
      <rect width="250" height="75" class="state-box" />
      <path d="M 0 6 Q 0 0 6 0 L 244 0 Q 250 0 250 6 L 250 24 L 0 24 Z" class="state-header" />
      <text x="125" y="17" class="state-name">檢閱全站日誌 (Browsing_All)</text>
      <text x="10" y="42" class="action-text">entry / 顯示所有使用者植物診斷記錄</text>
      <text x="10" y="56" class="action-text">do / 支援使用者帳號、作物、病害篩選</text>
      <text x="10" y="70" class="action-text">do / 檢視使用者備忘 (user_note) 與照片</text>
    </g>

    <line x1="270" y1="87" x2="330" y2="87" class="line" />
    <text x="300" y="80" class="transition-text" text-anchor="middle">點擊刪除按鈕</text>

    <!-- State 5: 刪除確認對話框 -->
    <g transform="translate(330, 50)">
      <rect width="280" height="85" class="danger-box" />
      <path d="M 0 6 Q 0 0 6 0 L 274 0 Q 280 0 280 6 L 280 24 L 0 24 Z" class="danger-header" />
      <text x="140" y="17" class="state-name" fill="#991b1b">二次刪除確認 (Deletion_Confirm)</text>
      <text x="10" y="42" class="action-text" fill="#b91c1c">entry / 彈出「確認安全刪除紀錄」警告視窗</text>
      <text x="10" y="56" class="action-text" fill="#b91c1c">do / 提示此操作將自 MySQL 徹底抹除不可復原</text>
      <text x="10" y="70" class="guard-text">[點擊取消] 返回日誌列表</text>
      <text x="10" y="82" class="guard-text">[點擊確認] 發送 DELETE /api/v1/admin/diaries/{id}</text>
    </g>

    <!-- State 6: 抹除與審計日誌更新 -->
    <g transform="translate(180, 165)">
      <rect width="280" height="75" class="danger-box" />
      <path d="M 0 6 Q 0 0 6 0 L 274 0 Q 280 0 280 6 L 280 24 L 0 24 Z" class="danger-header" />
      <text x="140" y="17" class="state-name" fill="#991b1b">資料庫安全清除 (Record_Purged)</text>
      <text x="10" y="42" class="action-text" fill="#b91c1c">do / 自 plant_diary 表格移除該筆資料</text>
      <text x="10" y="56" class="action-text" fill="#b91c1c">do / 同步刪除 static/uploads 磁碟圖片檔案</text>
      <text x="10" y="70" class="action-text" fill="#b91c1c">do / 即時刷新後台日誌列表，回傳 200 OK</text>
    </g>

    <path d="M 470 135 L 470 165 L 460 165" class="line" />
    <path d="M 180 202 L 145 202 L 145 125" class="line-back" />
    <text x="110" y="170" class="transition-text">刷新清單</text>
  </g>

  <!-- ================= SUB-PROCESS 2: FEEDBACK & ACTIVE LEARNING (UC-14) ================= -->
  <path d="M 290 260 L 450 260 L 450 480 L 480 480" class="line" />
  <text x="370" y="430" class="transition-text">審核糾錯反饋</text>

  <g transform="translate(480, 360)">
    <rect width="630" height="300" class="composite-bg" />
    <path d="M 0 8 Q 0 0 8 0 L 622 0 Q 630 0 630 8 L 630 30 L 0 30 Z" class="composite-header" fill="#dcfce7" />
    <text x="15" y="20" class="group-title" fill="#15803d">管理功能 2：糾錯審核與本地 ConvNet 模型持續訓練標註 (UC-14)</text>

    <!-- State 7: 審核糾錯反饋清單 -->
    <g transform="translate(20, 50)">
      <rect width="250" height="90" class="ai-box" />
      <path d="M 0 6 Q 0 0 6 0 L 244 0 Q 250 0 250 6 L 250 24 L 0 24 Z" class="ai-header" />
      <text x="125" y="17" class="state-name" fill="#15803d">反饋審查 (Reviewing_Feedback)</text>
      <text x="10" y="42" class="action-text">entry / 載入 diagnosis_feedback 待審清單</text>
      <text x="10" y="56" class="action-text">do / 比對原 AI 診斷與用戶糾錯標籤</text>
      <text x="10" y="70" class="action-text">do / 放大檢視病患葉片微觀病徵</text>
      <text x="10" y="84" class="action-text">do / 農學專家人工標註真值 (Ground Truth)</text>
    </g>

    <line x1="270" y1="95" x2="330" y2="95" class="line" />
    <text x="300" y="88" class="transition-text" text-anchor="middle">審核通過標註</text>

    <!-- State 8: 標註確認與入庫 -->
    <g transform="translate(330, 50)">
      <rect width="280" height="90" class="ai-box" />
      <path d="M 0 6 Q 0 0 6 0 L 274 0 Q 280 0 280 6 L 280 24 L 0 24 Z" class="ai-header" />
      <text x="140" y="17" class="state-name" fill="#15803d">專家標註確認 (Label_Confirmed)</text>
      <text x="10" y="42" class="action-text">do / 更新 diagnosis_feedback 狀態為已審查</text>
      <text x="10" y="56" class="action-text">do / 鎖定標註之真值作物與病害類別</text>
      <text x="10" y="70" class="action-text">do / 加入待微調樣本候選池 (Candidate Pool)</text>
      <text x="10" y="84" class="action-text">exit / 準備批次匯出訓練集</text>
    </g>

    <line x1="470" y1="140" x2="470" y2="185" class="line" />
    <text x="475" y="165" class="transition-text">點擊匯出訓練集</text>

    <!-- State 9: 匯出 JSONL 供 ConvNet 訓練 -->
    <g transform="translate(180, 185)">
      <rect width="400" height="95" class="ai-box" />
      <path d="M 0 6 Q 0 0 6 0 L 394 0 Q 400 0 400 6 L 400 24 L 0 24 Z" class="ai-header" />
      <text x="200" y="17" class="state-name" fill="#15803d">匯出訓練集供 ConvNet 訓練 (Export_JSONL)</text>
      <text x="10" y="42" class="action-text">do / 匯出審核回饋資料為標準標註訓練集 (Dataset Export)</text>
      <text x="10" y="56" class="action-text">do / 影像自動增強 (Data Augmentation) 擴增樣本集</text>
      <text x="10" y="70" class="action-text">do / 驅動本地 PyTorch ConvNet 卷積模型持續訓練 (Active Learning)</text>
      <text x="10" y="85" class="action-text">do / 迭代更新 convnet.pth 權重檔，零雲端託管端點開銷</text>
    </g>
  </g>
</svg>
"""

if __name__ == '__main__':
    svgs = {
        'documents/system_state_auth.svg': generate_svg_auth(),
        'documents/system_state_diagnosis.svg': generate_svg_diagnosis(),
        'documents/system_state_save_diary.svg': generate_svg_save_diary(),
        'documents/system_state_history.svg': generate_svg_history(),
        'documents/system_state_admin.svg': generate_svg_admin(),
    }
    for path, content in svgs.items():
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content.strip())
        print(f"Created {path}")
