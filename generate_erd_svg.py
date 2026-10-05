import os

svg_content = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1660 980" width="1660" height="980">
  <defs>
    <style>
      .title { font-family: 'Microsoft JhengHei', 'PingFang TC', sans-serif; font-size: 26px; font-weight: bold; fill: #000000; }
      .subtitle { font-family: 'Microsoft JhengHei', 'PingFang TC', sans-serif; font-size: 15px; font-weight: bold; fill: #000000; }
      .head { font-family: 'Microsoft JhengHei', 'PingFang TC', sans-serif; font-size: 17px; font-weight: bold; fill: #ffffff; }
      .field { font-family: 'Microsoft JhengHei', 'PingFang TC', 'Segoe UI', sans-serif; font-size: 14px; font-weight: 500; fill: #000000; }
      .field-bold { font-family: 'Microsoft JhengHei', 'PingFang TC', 'Segoe UI', sans-serif; font-size: 14px; font-weight: bold; fill: #000000; }
      .key-pk { font-family: 'Segoe UI', Arial, sans-serif; font-size: 13px; font-weight: bold; fill: #2D5837; }
      .key-fk { font-family: 'Segoe UI', Arial, sans-serif; font-size: 13px; font-weight: bold; fill: #456B4E; }
      .card-label { font-family: 'Segoe UI', Arial, sans-serif; font-size: 13px; font-weight: bold; fill: #000000; paint-order: stroke fill; stroke: #ffffff; stroke-width: 4.5px; stroke-linejoin: round; }

      .table-box { fill: #FFFFFF; stroke: #2D5837; stroke-width: 1.8; rx: 6; ry: 6; }
      .table-header { fill: #2D5837; }

      .line-req { stroke: #1A281E; stroke-width: 2.2; fill: none; }
      .line-opt { stroke: #1A281E; stroke-width: 2.0; stroke-dasharray: 7,4.5; fill: none; }
    </style>
  </defs>

  <!-- Background -->
  <rect width="100%" height="100%" fill="#ffffff" />

  <!-- Diagram Title & Subtitle -->
  <text x="830" y="45" class="title" text-anchor="middle">圖 8-1-1 資料庫實體關聯圖 (Entity-Relationship Diagram)</text>
  <text x="830" y="78" class="subtitle" text-anchor="middle">依現行 SQLAlchemy Models 繪製：實線為必填外鍵關聯 (1 : N)，虛線為可選關聯 (0..1 : N)</text>

  <!-- ========================================================================= -->
  <!-- COLUMN 1: USER & SECURITY (x=70, w=330)                                    -->
  <!-- ========================================================================= -->

  <!-- 1. user (y=130, h=240) -->
  <g transform="translate(70, 130)">
    <rect width="330" height="240" class="table-box" />
    <path d="M 0 6 Q 0 0 6 0 L 324 0 Q 330 0 330 6 L 330 42 L 0 42 Z" class="table-header" />
    <text x="165" y="27" text-anchor="middle" class="head">user (使用者)</text>
    
    <text x="18" y="70" class="key-pk">PK</text>
    <text x="56" y="70" class="field-bold">user_id</text>
    <text x="18" y="97" class="field">username · email</text>
    <text x="18" y="124" class="field">password_hash · full_name</text>
    <text x="18" y="151" class="field">role · is_email_verified</text>
    <text x="18" y="178" class="field">email_verified_at</text>
    <text x="18" y="205" class="field">created_at</text>
  </g>

  <!-- 2. user_one_time_tokens (y=420, h=210) -->
  <g transform="translate(70, 420)">
    <rect width="330" height="210" class="table-box" />
    <path d="M 0 6 Q 0 0 6 0 L 324 0 Q 330 0 330 6 L 330 42 L 0 42 Z" class="table-header" />
    <text x="165" y="27" text-anchor="middle" class="head">user_one_time_tokens (一次性權杖)</text>
    
    <text x="18" y="70" class="key-pk">PK</text>
    <text x="56" y="70" class="field-bold">id</text>
    <text x="18" y="97" class="key-fk">FK</text>
    <text x="56" y="97" class="field">user_id (NOT NULL)</text>
    <text x="18" y="124" class="field">purpose: String(32) · token_hash</text>
    <text x="18" y="151" class="field">expires_at · used_at</text>
    <text x="18" y="178" class="field">created_at</text>
  </g>

  <!-- 3. diagnosis_feedback (y=680, h=265) -->
  <g transform="translate(70, 680)">
    <rect width="330" height="265" class="table-box" />
    <path d="M 0 6 Q 0 0 6 0 L 324 0 Q 330 0 330 6 L 330 42 L 0 42 Z" class="table-header" />
    <text x="165" y="27" text-anchor="middle" class="head">diagnosis_feedback (診斷回饋)</text>
    
    <text x="18" y="68" class="key-pk">PK</text>
    <text x="56" y="68" class="field-bold">id</text>
    <text x="18" y="94" class="key-fk">FK?</text>
    <text x="56" y="94" class="field">user_id (可為匿名)</text>
    <text x="18" y="120" class="field">prediction_id (日誌序號對應)</text>
    <text x="18" y="146" class="field">image_url</text>
    <text x="18" y="172" class="field">original_plant_name · original_disease</text>
    <text x="18" y="198" class="field">is_plant_error · is_disease_error</text>
    <text x="18" y="224" class="field">corrected_plant · corrected_disease</text>
    <text x="18" y="250" class="field">created_at</text>
  </g>


  <!-- ========================================================================= -->
  <!-- COLUMN 2: MONITORING & CORE DIARY (x=490, w=440)                          -->
  <!-- ========================================================================= -->

  <!-- 4. webcam_alert (y=130, h=330) -->
  <g transform="translate(490, 130)">
    <rect width="440" height="330" class="table-box" />
    <path d="M 0 6 Q 0 0 6 0 L 434 0 Q 440 0 440 6 L 440 42 L 0 42 Z" class="table-header" />
    <text x="220" y="27" text-anchor="middle" class="head">webcam_alert (即時監控告警)</text>
    
    <text x="18" y="68" class="key-pk">PK</text>
    <text x="56" y="68" class="field-bold">id</text>
    <text x="18" y="94" class="key-fk">FK</text>
    <text x="56" y="94" class="field">user_id (NOT NULL)</text>
    <text x="18" y="120" class="key-fk">FK?</text>
    <text x="56" y="120" class="field">crop_id (可選作物關聯)</text>
    <text x="18" y="146" class="field">category · status_name</text>
    <text x="18" y="172" class="field">confidence · consecutive_matches (3影格)</text>
    <text x="18" y="198" class="field">requires_review · grounding_source</text>
    <text x="18" y="224" class="field">reference_source · reference_record_id</text>
    <text x="18" y="250" class="field">reference_url · session_id · region_id</text>
    <text x="18" y="276" class="field">image_url · email_sent</text>
    <text x="18" y="302" class="field">acknowledged_at · created_at</text>
  </g>

  <!-- 5. plant_diary (y=500, h=445) -->
  <g transform="translate(490, 500)">
    <rect width="440" height="445" class="table-box" />
    <path d="M 0 6 Q 0 0 6 0 L 434 0 Q 440 0 440 6 L 440 42 L 0 42 Z" class="table-header" />
    <text x="220" y="27" text-anchor="middle" class="head">plant_diary (植物診斷日誌)</text>
    
    <text x="18" y="66" class="key-pk">PK</text>
    <text x="56" y="66" class="field-bold">id</text>
    <text x="18" y="92" class="key-fk">FK</text>
    <text x="56" y="92" class="field">user_id · crop_id (NOT NULL)</text>
    <text x="18" y="118" class="key-fk">FK?</text>
    <text x="56" y="118" class="field">disease_id · pest_id (可選病蟲害)</text>
    <text x="18" y="144" class="field">category · status_name · confidence</text>
    <text x="18" y="170" class="field">requires_review · grounding_source</text>
    <text x="18" y="196" class="field">reference_source · reference_record_id</text>
    <text x="18" y="222" class="field">reference_url</text>
    <text x="18" y="248" class="field">image_url (圖片儲存路徑)</text>
    <text x="18" y="274" class="field">suggestion · treatment (處方措施)</text>
    <text x="18" y="300" class="field">user_note (個人備忘筆記)</text>
    <text x="18" y="326" class="field">user_corrected_status (糾錯狀態)</text>
    <text x="18" y="352" class="field">created_at</text>
  </g>


  <!-- ========================================================================= -->
  <!-- COLUMN 3: CROPS (x=1010, w=260)                                           -->
  <!-- ========================================================================= -->

  <!-- 6. crop (y=130, h=180) -->
  <g transform="translate(1010, 130)">
    <rect width="260" height="180" class="table-box" />
    <path d="M 0 6 Q 0 0 6 0 L 254 0 Q 260 0 260 6 L 260 42 L 0 42 Z" class="table-header" />
    <text x="130" y="27" text-anchor="middle" class="head">crop (作物)</text>
    
    <text x="18" y="70" class="key-pk">PK</text>
    <text x="56" y="70" class="field-bold">crop_id</text>
    <text x="18" y="105" class="field">crop_name (中文名稱)</text>
    <text x="18" y="138" class="field">crop_name_en (英文標籤)</text>
  </g>


  <!-- ========================================================================= -->
  <!-- COLUMN 4: DISEASES & PESTS (x=1350, w=260)                                -->
  <!-- ========================================================================= -->

  <!-- 7. disease (y=130, h=330) -->
  <g transform="translate(1350, 130)">
    <rect width="260" height="330" class="table-box" />
    <path d="M 0 6 Q 0 0 6 0 L 254 0 Q 260 0 260 6 L 260 42 L 0 42 Z" class="table-header" />
    <text x="130" y="27" text-anchor="middle" class="head">disease (病害資料庫)</text>
    
    <text x="18" y="68" class="key-pk">PK</text>
    <text x="56" y="68" class="field-bold">disease_id</text>
    <text x="18" y="96" class="key-fk">FK</text>
    <text x="56" y="96" class="field">crop_id</text>
    <text x="18" y="126" class="field">disease_name</text>
    <text x="18" y="156" class="field">description</text>
    <text x="18" y="186" class="field">treatment (防治處方)</text>
    <text x="18" y="216" class="field">source_name (農業部)</text>
    <text x="18" y="246" class="field">source_url</text>
    <text x="18" y="276" class="field">source_record_id</text>
  </g>

  <!-- 8. pests (y=520, h=330) -->
  <g transform="translate(1350, 520)">
    <rect width="260" height="330" class="table-box" />
    <path d="M 0 6 Q 0 0 6 0 L 254 0 Q 260 0 260 6 L 260 42 L 0 42 Z" class="table-header" />
    <text x="130" y="27" text-anchor="middle" class="head">pests (蟲害資料庫)</text>
    
    <text x="18" y="68" class="key-pk">PK</text>
    <text x="56" y="68" class="field-bold">pest_id</text>
    <text x="18" y="96" class="key-fk">FK</text>
    <text x="56" y="96" class="field">crop_id</text>
    <text x="18" y="126" class="field">pest_name</text>
    <text x="18" y="156" class="field">description</text>
    <text x="18" y="186" class="field">treatment (防治處方)</text>
    <text x="18" y="216" class="field">source_name (農業部)</text>
    <text x="18" y="246" class="field">source_url</text>
    <text x="18" y="276" class="field">source_record_id</text>
  </g>


  <!-- ========================================================================= -->
  <!-- RELATIONSHIP CONNECTORS                                                   -->
  <!-- ========================================================================= -->

  <!-- [1] user -> user_one_time_tokens -->
  <line x1="235" y1="370" x2="235" y2="420" class="line-req" />
  <text x="245" y="398" class="card-label">1 : N</text>

  <!-- [2] user -> diagnosis_feedback (Left Outer Corridor, x=35) -->
  <path d="M 70 280 L 35 280 L 35 815 L 70 815" class="line-opt" />
  <text x="35" y="550" class="card-label" text-anchor="middle">0..1 : N</text>

  <!-- [3] user -> webcam_alert (Straight Horizontal) -->
  <line x1="400" y1="190" x2="490" y2="190" class="line-req" />
  <text x="445" y="180" class="card-label" text-anchor="middle">1 : N</text>

  <!-- [4] user -> plant_diary -->
  <path d="M 400 270 L 445 270 L 445 560 L 490 560" class="line-req" />
  <text x="445" y="420" class="card-label" text-anchor="middle">1 : N</text>

  <!-- [5] crop -> webcam_alert (Optional, Straight Horizontal) -->
  <line x1="1010" y1="210" x2="930" y2="210" class="line-opt" />
  <text x="970" y="200" class="card-label" text-anchor="middle">0..1 : N</text>

  <!-- [6] crop -> plant_diary -->
  <path d="M 1010 270 L 970 270 L 970 560 L 930 560" class="line-req" />
  <text x="970" y="420" class="card-label" text-anchor="middle">1 : N</text>

  <!-- [7] crop -> disease (Straight Horizontal) -->
  <line x1="1270" y1="190" x2="1350" y2="190" class="line-req" />
  <text x="1310" y="180" class="card-label" text-anchor="middle">1 : N</text>

  <!-- [8] crop -> pests -->
  <path d="M 1270 250 L 1310 250 L 1310 580 L 1350 580" class="line-req" />
  <text x="1310" y="480" class="card-label" text-anchor="middle">1 : N</text>

  <!-- [9] disease -> plant_diary (Spacious Corridor at x=1150) -->
  <path d="M 1350 380 L 1150 380 L 1150 650 L 930 650" class="line-opt" />
  <text x="1230" y="370" class="card-label" text-anchor="middle">0..1 : N</text>

  <!-- [10] pests -> plant_diary (Straight Horizontal) -->
  <line x1="1350" y1="740" x2="930" y2="740" class="line-opt" />
  <text x="1140" y="730" class="card-label" text-anchor="middle">0..1 : N</text>

</svg>
"""

targets = [
    "documents/圖/圖 8-1-1 資料庫實體關聯圖.svg",
    "documents/system_erd.svg",
]

for t in targets:
    with open(t, "w", encoding="utf-8") as f:
        f.write(svg_content.strip())
    print(f"Written to {t}")
