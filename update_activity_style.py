# Script to update documents/system_activity_diagnosis.svg with Plan A logic:
# - Unknown plants hide save button and only allow feedback / error report.
# - Confirmed plants allow save or feedback.
# - Pure black bold text, spacious nodes, independent final nodes.

svg_content = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 890" width="1200" height="890">
  <defs>
    <style>
      .title { font-family: 'Microsoft JhengHei', 'PingFang TC', sans-serif; font-size: 20px; font-weight: bold; fill: #0f172a; }
      .swimlane-title { font-family: 'Microsoft JhengHei', 'PingFang TC', sans-serif; font-size: 15px; font-weight: bold; fill: #0f172a; text-anchor: middle; }
      .node-title { font-family: 'Microsoft JhengHei', 'PingFang TC', sans-serif; font-size: 13.5px; font-weight: 800; fill: #0f172a; text-anchor: middle; }
      /* Subtext: Pure solid black (#000000), bold, 11.5px - 100% contrast, crystal clear readability */
      .node-subtext { font-family: 'Microsoft JhengHei', 'PingFang TC', sans-serif; font-size: 11.5px; font-weight: bold; fill: #000000; text-anchor: middle; }
      .edge-label { font-family: 'Microsoft JhengHei', 'PingFang TC', sans-serif; font-size: 11px; font-weight: bold; text-anchor: middle; }
      
      .swimlane-bg { fill: #f8fafc; stroke: #cbd5e1; stroke-width: 1.5; }
      .swimlane-header { fill: #e2e8f0; stroke: #cbd5e1; stroke-width: 1.5; }
      
      .action-node { fill: #ffffff; stroke: #2563eb; stroke-width: 1.8; rx: 8; ry: 8; filter: drop-shadow(0 2px 4px rgba(0,0,0,0.06)); }
      .ai-node { fill: #f0fdf4; stroke: #16a34a; stroke-width: 1.8; rx: 8; ry: 8; filter: drop-shadow(0 2px 4px rgba(0,0,0,0.06)); }
      .db-node { fill: #fefce8; stroke: #ca8a04; stroke-width: 1.8; rx: 8; ry: 8; filter: drop-shadow(0 2px 4px rgba(0,0,0,0.06)); }
      .warn-node { fill: #fff7ed; stroke: #ea580c; stroke-width: 1.8; rx: 8; ry: 8; filter: drop-shadow(0 2px 4px rgba(0,0,0,0.06)); }
      .decision-node { fill: #eff6ff; stroke: #2563eb; stroke-width: 1.8; }
      .sync-bar { fill: #0f172a; }
      .line { stroke: #334155; stroke-width: 1.8; fill: none; marker-end: url(#arrow); }
      .dashed-line { stroke: #475569; stroke-width: 1.8; stroke-dasharray: 4,4; fill: none; marker-end: url(#arrow); }
      .label-badge { fill: #ffffff; stroke: #94a3b8; stroke-width: 1.2; rx: 4; ry: 4; }
    </style>
    <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M 0 1 L 10 5 L 0 9 z" fill="#334155" />
    </marker>
  </defs>

  <!-- Background -->
  <rect width="100%" height="100%" fill="#ffffff" />
  
  <!-- Diagram Title -->
  <text x="600" y="32" class="title" text-anchor="middle">圖 5-3-1 植物病害診斷流程活動圖 (Activity Diagram)</text>

  <!-- Swimlane 1: 使用者 (Android App) -->
  <rect x="40" y="55" width="280" height="810" class="swimlane-bg" />
  <rect x="40" y="55" width="280" height="40" class="swimlane-header" />
  <text x="180" y="80" class="swimlane-title">使用者與 Android 端 (Client)</text>

  <!-- Swimlane 2: FastAPI 後端服務 -->
  <rect x="320" y="55" width="280" height="810" class="swimlane-bg" />
  <rect x="320" y="55" width="280" height="40" class="swimlane-header" />
  <text x="460" y="80" class="swimlane-title">FastAPI 後端微服務 (Server)</text>

  <!-- Swimlane 3: AI 雙模型協同推論核心 -->
  <rect x="600" y="55" width="300" height="810" class="swimlane-bg" />
  <rect x="600" y="55" width="300" height="40" class="swimlane-header" />
  <text x="750" y="80" class="swimlane-title">AI 雙模型協同推論核心 (Dual-Model)</text>

  <!-- Swimlane 4: FAISS 向量知識庫與資料庫 -->
  <rect x="900" y="55" width="260" height="810" class="swimlane-bg" />
  <rect x="900" y="55" width="260" height="40" class="swimlane-header" />
  <text x="1030" y="80" class="swimlane-title">知識檢索與資料庫 (RAG &amp; DB)</text>

  <!-- Start Node -->
  <circle cx="180" cy="120" r="14" fill="#0f172a" />
  <line x1="180" y1="134" x2="180" y2="160" class="line" />

  <!-- Action: 拍照或選取植物病徵照片 -->
  <rect x="80" y="160" width="200" height="52" class="action-node" />
  <text x="180" y="182" class="node-title">拍照或選取照片</text>
  <text x="180" y="200" class="node-subtext">選擇患病作物葉片影像</text>

  <line x1="180" y1="212" x2="180" y2="235" class="line" />

  <!-- Action: 發起診斷請求 -->
  <rect x="80" y="235" width="200" height="52" class="action-node" />
  <text x="180" y="257" class="node-title">發起診斷分析請求</text>
  <text x="180" y="275" class="node-subtext">POST /api/v1/predict (帶 JWT)</text>

  <!-- Flow to Server -->
  <path d="M 280 261 L 360 261" class="line" />

  <!-- Action: 影像接收與快取生成 -->
  <rect x="360" y="235" width="200" height="52" class="action-node" />
  <text x="460" y="257" class="node-title">接收影像並暫存快取</text>
  <text x="460" y="275" class="node-subtext">生成 prediction_id 追蹤號</text>

  <line x1="460" y1="287" x2="460" y2="315" class="line" />

  <!-- Fork Bar (並行派發) -->
  <rect x="350" y="315" width="220" height="8" rx="4" class="sync-bar" />

  <!-- Parallel Branch 1: Gemini 2.5 Flash -->
  <path d="M 410 323 L 410 355 L 620 355" class="line" />
  <rect x="620" y="330" width="260" height="52" class="ai-node" />
  <text x="750" y="352" class="node-title">Gemini 2.5 Flash 雲端多模態推論</text>
  <text x="750" y="370" class="node-subtext">廣域視覺初判、病徵語意描述與嚴重度</text>

  <!-- Parallel Branch 2: Local ConvNet -->
  <path d="M 510 323 L 510 415 L 620 415" class="line" />
  <rect x="620" y="390" width="260" height="52" class="ai-node" />
  <text x="750" y="412" class="node-title">本地自訓特定作物 ConvNet 推論</text>
  <text x="750" y="430" class="node-subtext">局部病斑微觀分類與機率 (零雲端成本)</text>

  <!-- Join Bar (推論結果聚合) -->
  <path d="M 880 355 L 895 355 L 895 455 L 830 455" class="line" />
  <path d="M 880 415 L 895 415 L 895 455 L 830 455" class="line" />
  <rect x="640" y="455" width="220" height="8" rx="4" class="sync-bar" />

  <line x1="750" y1="463" x2="750" y2="485" class="line" />

  <!-- Action: 多模型決策仲裁與衝突比對 -->
  <rect x="620" y="485" width="260" height="52" class="action-node" />
  <text x="750" y="507" class="node-title">多模型決策仲裁核心</text>
  <text x="750" y="525" class="node-subtext">比對雙模型分類標籤、置信權重與特徵互補</text>

  <!-- Query FAISS RAG and DB -->
  <path d="M 880 511 L 920 511" class="line" />
  <rect x="920" y="485" width="220" height="52" class="db-node" />
  <text x="1030" y="507" class="node-title">FAISS 向量檢索與知識校驗</text>
  <text x="1030" y="525" class="node-subtext">農業部開放資料客觀比對 (防幻覺)</text>

  <!-- Back from RAG to Decision -->
  <path d="M 1030 537 L 1030 565 L 750 565" class="line" />

  <!-- Decision: 置信度門檻 (70%) -->
  <polygon points="750,565 805,590 750,615 695,590" class="decision-node" />
  <text x="750" y="594" class="node-title" font-size="12">信心度 ≥ 70% ?</text>

  <!-- Branch [是]: 判定確診病害 -->
  <path d="M 695 590 L 675 590 L 675 625" class="line" />
  <rect x="648" y="578" width="28" height="18" class="label-badge" />
  <text x="662" y="591" class="edge-label" fill="#16a34a">[是]</text>
  
  <rect x="605" y="625" width="140" height="50" class="action-node" />
  <text x="675" y="646" class="node-title">判定確診病害</text>
  <text x="675" y="663" class="node-subtext">綁定官方權威防治指南</text>

  <!-- Branch [否]: 標註「未知/無法判定」與需專家覆核 -->
  <path d="M 805 590 L 825 590 L 825 625" class="line" />
  <rect x="806" y="578" width="28" height="18" class="label-badge" />
  <text x="820" y="591" class="edge-label" fill="#dc2626">[否]</text>

  <rect x="755" y="625" width="140" height="50" class="warn-node" />
  <text x="825" y="646" class="node-title" fill="#9a3412">標註「未知/無法判定」</text>
  <text x="825" y="663" class="node-subtext">需專家覆核與保守處置</text>

  <!-- Merge: Flow from both branches to Server JSON aggregation -->
  <path d="M 675 675 L 675 691 L 560 691" class="line" />
  <path d="M 825 675 L 825 691 L 560 691" class="line" />

  <!-- Action: 整合回傳結構化診斷 JSON -->
  <rect x="360" y="665" width="200" height="52" class="action-node" />
  <text x="460" y="687" class="node-title">整合診斷報告 JSON</text>
  <text x="460" y="705" class="node-subtext">病名/信心度/處置指引/覆核標記</text>

  <!-- Send back to Client -->
  <path d="M 360 691 L 280 691" class="line" />

  <!-- Action: 客戶端呈現詳細診斷報告 (註明未知時的 UI 特徵) -->
  <rect x="70" y="665" width="220" height="52" class="action-node" />
  <text x="180" y="687" class="node-title">呈現圖文診斷報告</text>
  <text x="180" y="705" class="node-subtext">展示病斑特徵；若未知則隱藏儲存按鈕</text>

  <line x1="180" y1="717" x2="180" y2="745" class="line" />

  <!-- Decision: 使用者後續操作 -->
  <polygon points="180,745 235,770 180,795 125,770" class="decision-node" />
  <text x="180" y="774" class="node-title" font-size="12">後續操作選擇</text>

  <!-- Branch 1: 確診病害且確認儲存 -->
  <path d="M 235 770 L 360 770" class="line" />
  <!-- Badge for [確診且確認儲存] placed cleanly above line -->
  <rect x="250" y="744" width="98" height="20" class="label-badge" />
  <text x="299" y="758" class="edge-label" fill="#16a34a">[確診且確認儲存]</text>
  
  <rect x="360" y="746" width="200" height="48" class="action-node" />
  <text x="460" y="766" class="node-title">持久化至 plant_diary</text>
  <text x="460" y="783" class="node-subtext">關聯筆記 (未知病害禁止存入)</text>

  <path d="M 560 770 L 915 770" class="line" />
  <rect x="915" y="746" width="200" height="48" class="db-node" />
  <text x="1015" y="766" class="node-title">寫入 plant_diary 資料表</text>
  <text x="1015" y="783" class="node-subtext">儲存病害紀錄與正式圖片路徑</text>

  <!-- Branch 1 Final Node: 儲存成功流程結束 -->
  <line x1="1115" y1="770" x2="1140" y2="770" class="line" />
  <circle cx="1155" cy="770" r="10" fill="#0f172a" />
  <circle cx="1155" cy="770" r="14" fill="none" stroke="#0f172a" stroke-width="2" />

  <!-- Branch 2: 提交診斷反饋糾錯 (未知植物僅保留此選項) -->
  <path d="M 125 770 L 48 770 L 48 835 L 360 835" class="line" />
  <!-- Badge for [反饋糾錯 / 結果有誤]: Placed above line with zero collision -->
  <rect x="52" y="744" width="105" height="20" class="label-badge" />
  <text x="104" y="758" class="edge-label" fill="#7c3aed">[反饋糾錯 / 結果有誤]</text>

  <rect x="360" y="811" width="200" height="48" class="action-node" />
  <text x="460" y="831" class="node-title">寫入 diagnosis_feedback</text>
  <text x="460" y="848" class="node-subtext">糾錯標籤存檔 (未知植物僅此項)</text>

  <path d="M 560 835 L 915 835" class="line" />
  <rect x="915" y="811" width="200" height="48" class="db-node" />
  <text x="1015" y="831" class="node-title">寫入 feedback 資料表</text>
  <text x="1015" y="848" class="node-subtext">儲存糾錯反饋提供模型複訓</text>

  <!-- Branch 2 Final Node: 反饋提交成功流程結束 -->
  <line x1="1115" y1="835" x2="1140" y2="835" class="line" />
  <circle cx="1155" cy="835" r="10" fill="#0f172a" />
  <circle cx="1155" cy="835" r="14" fill="none" stroke="#0f172a" stroke-width="2" />

</svg>
"""

with open('documents/system_activity_diagnosis.svg', 'w', encoding='utf-8') as f:
    f.write(svg_content.strip())
print("Successfully regenerated system_activity_diagnosis.svg with Plan A logic!")
