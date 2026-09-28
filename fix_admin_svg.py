import re

with open('documents/system_state_admin.svg', 'r', encoding='utf-8') as f:
    svg = f.read()

# Replace the connector and text between State 4 and State 5
old_str = """    <!-- State 4: 檢閱全站日誌清單 -->
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
    <g transform="translate(330, 50)">"""

new_str = """    <!-- State 4: 檢閱全站日誌清單 -->
    <g transform="translate(15, 50)">
      <rect width="240" height="75" class="state-box" />
      <path d="M 0 6 Q 0 0 6 0 L 234 0 Q 240 0 240 6 L 240 24 L 0 24 Z" class="state-header" />
      <text x="120" y="17" class="state-name">檢閱全站日誌 (Browsing_All)</text>
      <text x="10" y="42" class="action-text">entry / 顯示所有使用者植物診斷記錄</text>
      <text x="10" y="56" class="action-text">do / 支援使用者帳號、作物、病害篩選</text>
      <text x="10" y="70" class="action-text">do / 檢視使用者備忘 (user_note) 與照片</text>
    </g>

    <line x1="255" y1="87" x2="345" y2="87" class="line" />
    <rect x="260" y="70" width="80" height="15" fill="#ffffff" rx="3" />
    <text x="300" y="82" class="transition-text" text-anchor="middle">點擊刪除按鈕</text>

    <!-- State 5: 刪除確認對話框 -->
    <g transform="translate(345, 50)">"""

if old_str in svg:
    svg = svg.replace(old_str, new_str)
    with open('documents/system_state_admin.svg', 'w', encoding='utf-8') as f:
        f.write(svg)
    print("Fixed overlap in system_state_admin.svg")
else:
    print("Pattern not found, will rewrite")
