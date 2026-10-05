import os
import sys
from xml.sax.saxutils import escape
import docx
from docx.oxml import parse_xml
from docx.oxml.ns import qn

sys.stdout.reconfigure(encoding='utf-8')


def build_h2_p(text):
    xml = f"""<w:p xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:pPr>
    <w:pStyle w:val="21"/>
    <w:keepNext/>
    <w:ind w:left="847" w:right="280"/>
    <w:spacing w:before="240" w:after="120"/>
    <w:rPr>
      <w:rFonts w:ascii="微軟正黑體" w:hAnsi="微軟正黑體" w:eastAsia="微軟正黑體"/>
      <w:color w:val="auto"/>
      <w:b/>
      <w:sz w:val="28"/>
      <w:szCs w:val="28"/>
      <w:lang w:eastAsia="zh-TW"/>
    </w:rPr>
  </w:pPr>
  <w:r>
    <w:rPr>
      <w:rFonts w:ascii="微軟正黑體" w:hAnsi="微軟正黑體" w:eastAsia="微軟正黑體"/>
      <w:color w:val="auto"/>
      <w:b/>
      <w:sz w:val="28"/>
      <w:szCs w:val="28"/>
      <w:lang w:eastAsia="zh-TW"/>
    </w:rPr>
    <w:t>{escape(text)}</w:t>
  </w:r>
</w:p>"""
    return parse_xml(xml)


def build_h3_p(text):
    xml = f"""<w:p xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:pPr>
    <w:keepNext/>
    <w:ind w:left="847" w:right="280"/>
    <w:spacing w:before="180" w:after="80"/>
    <w:rPr>
      <w:rFonts w:ascii="微軟正黑體" w:hAnsi="微軟正黑體" w:eastAsia="微軟正黑體"/>
      <w:color w:val="1F497D"/>
      <w:b/>
      <w:sz w:val="24"/>
      <w:szCs w:val="24"/>
      <w:lang w:eastAsia="zh-TW"/>
    </w:rPr>
  </w:pPr>
  <w:r>
    <w:rPr>
      <w:rFonts w:ascii="微軟正黑體" w:hAnsi="微軟正黑體" w:eastAsia="微軟正黑體"/>
      <w:color w:val="1F497D"/>
      <w:b/>
      <w:sz w:val="24"/>
      <w:szCs w:val="24"/>
      <w:lang w:eastAsia="zh-TW"/>
    </w:rPr>
    <w:t>{escape(text)}</w:t>
  </w:r>
</w:p>"""
    return parse_xml(xml)


def build_normal_p(text, indent_first_line=True, is_bullet=False):
    first_line_attr = ' w:firstLine="454"' if indent_first_line and not is_bullet else ''
    left_indent = "847" if is_bullet else "280"
    spacing_after = "60" if is_bullet else "120"
    xml = f"""<w:p xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:pPr>
    <w:ind w:left="{left_indent}" w:right="280"{first_line_attr}/>
    <w:spacing w:line="360" w:lineRule="auto" w:after="{spacing_after}"/>
    <w:rPr>
      <w:rFonts w:hint="eastAsia"/>
      <w:lang w:eastAsia="zh-TW"/>
    </w:rPr>
  </w:pPr>
  <w:r>
    <w:rPr>
      <w:rFonts w:ascii="微軟正黑體" w:hAnsi="微軟正黑體" w:eastAsia="微軟正黑體"/>
      <w:sz w:val="24"/>
      <w:szCs w:val="24"/>
      <w:lang w:eastAsia="zh-TW"/>
    </w:rPr>
    <w:t>{escape(text)}</w:t>
  </w:r>
</w:p>"""
    return parse_xml(xml)


def build_code_p(code_lines):
    xml_parts = [
        '<w:p xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">',
        '  <w:pPr>',
        '    <w:pBdr>',
        '      <w:top w:val="single" w:sz="4" w:space="4" w:color="D3D3D3"/>',
        '      <w:left w:val="single" w:sz="18" w:space="8" w:color="4A86E8"/>',
        '      <w:bottom w:val="single" w:sz="4" w:space="4" w:color="D3D3D3"/>',
        '      <w:right w:val="single" w:sz="4" w:space="4" w:color="D3D3D3"/>',
        '    </w:pBdr>',
        '    <w:shd w:val="clear" w:color="auto" w:fill="F5F7FA"/>',
        '    <w:ind w:left="560" w:right="280"/>',
        '    <w:spacing w:line="280" w:lineRule="auto" w:before="80" w:after="140"/>',
        '    <w:rPr>',
        '      <w:rFonts w:ascii="Consolas" w:hAnsi="Consolas" w:eastAsia="微軟正黑體"/>',
        '      <w:color w:val="24292E"/>',
        '      <w:sz w:val="20"/>',
        '      <w:szCs w:val="20"/>',
        '      <w:lang w:eastAsia="zh-TW"/>',
        '    </w:rPr>',
        '  </w:pPr>',
        '  <w:r>',
        '    <w:rPr>',
        '      <w:rFonts w:ascii="Consolas" w:hAnsi="Consolas" w:eastAsia="微軟正黑體"/>',
        '      <w:color w:val="24292E"/>',
        '      <w:sz w:val="20"/>',
        '      <w:szCs w:val="20"/>',
        '      <w:lang w:eastAsia="zh-TW"/>',
        '    </w:rPr>'
    ]
    for idx, line in enumerate(code_lines):
        if idx > 0:
            xml_parts.append('    <w:br/>')
        xml_parts.append(f'    <w:t xml:space="preserve">{escape(line)}</w:t>')
    xml_parts.append('  </w:r>')
    xml_parts.append('</w:p>')
    return parse_xml(''.join(xml_parts))


def build_chapter_11_elements():
    """Generates all XML elements for Chapter 11 (操作手冊)."""
    elements = []

    # 11-1 系統架構與核心元件職責
    elements.append(build_h2_p('11-1 系統架構與核心元件職責'))
    elements.append(build_normal_p('本系統採用前後端完全分離之現代化微服務設計架構，各元件間職責分明且具備高度解耦性，主要由以下五大核心元件協同運作：'))
    elements.append(build_normal_p('1. 前端行動應用 (Android Mobile App)：基於 Kotlin 語言開發，整合 ViewBinding、CameraX 與 Retrofit2。提供農友直覺操作介面，支援相機對焦拍攝、相簿選圖、即時診斷視覺化呈現、個人日誌管理、備忘記事編輯（UC-08）與誤判回饋提報。', is_bullet=True))
    elements.append(build_normal_p('2. 後端服務引擎 (FastAPI Backend)：採用 Python 3.11 與高效能 FastAPI 框架，擔任全系統業務調度中樞。負責 RESTful API 路由分發、JWT 權限鑑權、SMTP 信箱驗證與警報寄發、影像檢驗、雙層 AI 診斷排程、三方仲裁器決策及 FAISS 向量檢索。', is_bullet=True))
    elements.append(build_normal_p('3. 資料庫持久化系統 (MySQL 8.0)：採用 MySQL 8.0 InnoDB 引擎搭配 SQLAlchemy ORM 與 Alembic 版本控制庫。持久化儲存會員帳號、Argon2 密碼雜湊、一次性權杖、官方作物病蟲害基礎資料庫、植物日誌快照與視訊警報紀錄；實體圖片保存於靜態目錄。', is_bullet=True))
    elements.append(build_normal_p('4. 雙層 AI 協同診斷引擎 (Local ConvNeXt + Cloud Gemini)：提供階層式推論架構。第一層由本地 ConvNeXt-Tiny 模型進行毫秒級（<500ms）常見 15 類病害快篩；低信心或複雜病斑則降級至第二層 Gemini 多模態雲端模型進行深層辨析，並由三方仲裁器綜合裁決杜絕大模型幻覺。', is_bullet=True))
    elements.append(build_normal_p('5. 檢索增強向量知識庫 (FAISS RAG Knowledge Base)：以 FAISS 密集向量索引庫整合農業部官方病蟲害專書文本庫（data.json）。當診斷命中病害時，自動檢索語意最相近之權威文獻，將防護處置建議精準注入診斷報告，提供具可追溯來源依據之農業防護指南。', is_bullet=True))

    # 11-2 系統安裝與環境設定
    elements.append(build_h2_p('11-2 系統安裝與環境設定'))
    elements.append(build_h3_p('11-2-1 前置軟硬體環境需求'))
    elements.append(build_normal_p('• 作業系統：Windows 10/11、Ubuntu 22.04 LTS 或 macOS Monterey 以上作業系統。', is_bullet=True))
    elements.append(build_normal_p('• 後端環境：Python 3.10 或 3.11、MySQL 8.0 資料庫伺服器、Git 版本控制工具。', is_bullet=True))
    elements.append(build_normal_p('• 前端環境：Android Studio Ladybug (2024.2+) 或更高版本、JDK 17、Android SDK Platform 34。', is_bullet=True))
    elements.append(build_normal_p('• 容器環境（選用）：Docker Engine 24+ 及 Docker Compose v2+。', is_bullet=True))
    elements.append(build_normal_p('• 金鑰與憑證：Google Gemini API Key、Gmail 應用程式密碼（用於 SMTP 寄送驗證信與警報通知）。', is_bullet=True))

    elements.append(build_h3_p('11-2-2 步驟 1：取得專案原始碼'))
    elements.append(build_normal_p('開啟終端機（PowerShell 或 Bash），使用 Git 指令將專案儲存庫複製至本地端，並切換至專案根目錄：'))
    elements.append(build_code_p([
        'git clone https://github.com/11436022/plant.git',
        'cd plant'
    ]))

    elements.append(build_h3_p('11-2-3 步驟 2：建立 Python 虛擬環境並安裝相依套件'))
    elements.append(build_normal_p('為確保環境純淨並避免套件版本衝突，強烈建議建立專用的 Python 虛擬隔離環境：'))
    elements.append(build_code_p([
        '# 建立虛擬環境',
        'python -m venv venv',
        '',
        '# 啟動虛擬環境 (Windows PowerShell)',
        '.\\venv\\Scripts\\activate',
        '',
        '# 啟動虛擬環境 (Linux / macOS)',
        'source venv/bin/activate',
        '',
        '# 升級 pip 並安裝後端相依套件',
        'python -m pip install --upgrade pip',
        'pip install -r requirements.txt'
    ]))

    elements.append(build_h3_p('11-2-4 步驟 3：配置環境變數組態檔案 (.env)'))
    elements.append(build_normal_p('複製專案隨附之 .env.example 範本檔案並重新命名為 .env，並設定連線密鑰與第三方服務憑證：'))
    elements.append(build_code_p([
        '# 複製環境變數範本 (Windows PowerShell)',
        'Copy-Item .env.example .env',
        '',
        '# 複製環境變數範本 (Linux / macOS)',
        'cp .env.example .env'
    ]))
    elements.append(build_normal_p('編輯 .env 檔案，填入關鍵設定（包含 GEMINI_API_KEY、DB_HOST、DB_USER、DB_PASSWORD、DB_NAME、JWT_SECRET_KEY 及 SMTP 郵件憑證等）：'))
    elements.append(build_code_p([
        'GEMINI_API_KEY=your_actual_gemini_api_key',
        'DB_HOST=127.0.0.1',
        'DB_PORT=3306',
        'DB_USER=plant',
        'DB_PASSWORD=your_secure_password',
        'DB_NAME=plant_db',
        'JWT_SECRET_KEY=generate_a_long_random_secret_key_at_least_32_chars',
        'SMTP_HOST=smtp.gmail.com',
        'SMTP_PORT=587',
        'SMTP_USERNAME=your_gmail_account@gmail.com',
        'SMTP_PASSWORD=your_gmail_app_password',
        'SMTP_FROM_EMAIL=your_gmail_account@gmail.com'
    ]))

    elements.append(build_h3_p('11-2-5 步驟 4：本地 AI 模型權重配置'))
    elements.append(build_normal_p('本系統採用雙模型邊緣快篩架構。請確認已將 PyTorch 訓練權重檔 convnext_plant_best.pth 與類別雙向映射字典檔案 idx_to_class.json 放置於專案根目錄。若未放置權重檔，系統將自動啟動安全降級機制，改由雲端 Gemini 進行全權診斷。'))

    # 11-3 資料庫遷移與知識庫建置
    elements.append(build_h2_p('11-3 資料庫遷移與知識庫建置'))
    elements.append(build_h3_p('11-3-1 步驟 1：建立 MySQL 資料庫與授權帳號'))
    elements.append(build_normal_p('登入 MySQL 終端或管理工具，建立系統專用之資料庫實例並指派連線權限：'))
    elements.append(build_code_p([
        'CREATE DATABASE plant_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;',
        "CREATE USER 'plant'@'%' IDENTIFIED BY 'your_secure_password';",
        "GRANT ALL PRIVILEGES ON plant_db.* TO 'plant'@'%';",
        'FLUSH PRIVILEGES;'
    ]))

    elements.append(build_h3_p('11-3-2 步驟 2：執行 Alembic 資料庫版本遷移'))
    elements.append(build_normal_p('透過 Alembic 工具將最新資料庫綱要（包含診斷來源快照、複核註記、Webcam 警報及使用者糾錯資料表）自動同步至 MySQL：'))
    elements.append(build_code_p([
        '# 執行遷移至最新版本 (head)',
        'python -m alembic upgrade head',
        '',
        '# 核對目前資料庫版本狀態',
        'python -m alembic current'
    ]))

    elements.append(build_h3_p('11-3-3 步驟 3：匯入官方農業基礎種子資料'))
    elements.append(build_normal_p('執行種子資料匯入腳本，將農業部認證之作物類別、常見病害與常見蟲害圖鑑資料庫以冪等（Idempotent）方式寫入資料庫：'))
    elements.append(build_code_p([
        'python seed.py'
    ]))

    elements.append(build_h3_p('11-3-4 步驟 4：建立 FAISS 向量知識庫與檢驗清單'))
    elements.append(build_normal_p('執行 RAG 向量知識庫建庫腳本，將 data.json 農業文獻轉換為語意密集特徵向量庫，並生成包含 SHA-256 雜湊檢核之元數據清單：'))
    elements.append(build_code_p([
        'python build_knowledge_base.py'
    ]))
    elements.append(build_normal_p('建庫完成後，將於專案根目錄生成成對之向量索引檔案 knowledge_base.faiss 與清單檔案 knowledge_content.json。'))

    # 11-4 系統啟動與服務驗證
    elements.append(build_h2_p('11-4 系統啟動與服務驗證'))
    elements.append(build_h3_p('11-4-1 步驟 1：啟動後端 FastAPI 伺服器'))
    elements.append(build_normal_p('於已啟動虛擬環境的專案根目錄下，執行後端啟動指令：'))
    elements.append(build_code_p([
        '# 方式 A：透過專案進入點執行',
        'python main.py',
        '',
        '# 方式 B：透過 Uvicorn 伺服器掛載熱重載 (推薦開發模式)',
        'uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload'
    ]))
    elements.append(build_normal_p('終端機輸出 Application startup complete. 即代表伺服器已成功運行於 http://0.0.0.0:8000。'))

    elements.append(build_h3_p('11-4-2 步驟 2：OpenAPI 互動式文件與健康檢查'))
    elements.append(build_normal_p('開啟瀏覽器測試核心端點以確認服務健康狀態：'))
    elements.append(build_normal_p('1. 健康檢查端點：存取 http://127.0.0.1:8000/api/v1/health，應回傳 {"status": "ok", "app": "plant_diagnosis_api"}。', is_bullet=True))
    elements.append(build_normal_p('2. Swagger API 互動文件：存取 http://127.0.0.1:8000/docs，可檢視完整之 20+ 個 RESTful API 端點規格與即時測試介面。', is_bullet=True))

    elements.append(build_h3_p('11-4-3 步驟 3：管理員帳號初次建立與驗證'))
    elements.append(build_normal_p('透過註冊端點註冊管理者電子郵件，收取驗證碼完成信箱啟用後，於 MySQL 將該帳號的 role 欄位更新為 admin，即可解鎖管理後台權限：'))
    elements.append(build_code_p([
        "UPDATE user SET role = 'admin' WHERE email = 'your_admin_email@domain.com';"
    ]))

    # 11-5 Docker 容器化快速部署
    elements.append(build_h2_p('11-5 Docker 容器化快速部署'))
    elements.append(build_h3_p('11-5-1 容器化架構特性'))
    elements.append(build_normal_p('• 輕量與高性能：基於 python:3.11-slim 輕量映像檔，預載 OpenMP 函式庫以發揮 FAISS 向量運算最大效能。', is_bullet=True))
    elements.append(build_normal_p('• 高安全性：容器內部採用非 root (appuser) 權限執行，有效防止容器逃逸威脅。', is_bullet=True))
    elements.append(build_normal_p('• 跨平台主機連線：內建 host-gateway 網路映射，容器可直接以 DB_HOST=host.docker.internal 連線至主機 MySQL 資料庫。', is_bullet=True))
    elements.append(build_normal_p('• 持久化儲存保證：主機端 ./static/uploads 與 ./static/feedback_uploads 目錄自動掛載，重啟或升級容器資料不遺失。', is_bullet=True))

    elements.append(build_h3_p('11-5-2 一鍵建置與啟動指令'))
    elements.append(build_normal_p('確保 Docker Desktop 已啟動，於專案根目錄執行以下指令進行一鍵啟動與監控：'))
    elements.append(build_code_p([
        '# 建置並於背景啟動容器服務',
        'docker compose up -d --build',
        '',
        '# 檢查容器運行狀態',
        'docker compose ps',
        '',
        '# 即時檢視容器日誌輸出',
        'docker compose logs -f plant-backend',
        '',
        '# 停止容器服務',
        'docker compose down'
    ]))

    # 11-6 Android 行動客戶端建置與連線
    elements.append(build_h2_p('11-6 Android 行動客戶端建置與連線'))
    elements.append(build_h3_p('11-6-1 開發環境準備'))
    elements.append(build_normal_p('使用 Android Studio Ladybug (2024.2+) 或更高版本開啟專案子目錄 frontend/plantdoctor。確認 Gradle JDK 設定為 JDK 17，專案支援 Android SDK 26 至 34。'))

    elements.append(build_h3_p('11-6-2 伺服器連線 IP 位址配置'))
    elements.append(build_normal_p('開啟 RetrofitClient.kt（或 Constants.kt），依據測試情境設定後端 API 伺服器位址：'))
    elements.append(build_code_p([
        '// 情境 A：使用 Android Studio 內建模擬器 (Emulator)',
        'private const val BASE_URL = "http://10.0.2.2:8000/api/v1/"',
        '',
        '// 情境 B：使用實體 Android 手機進行 Wi-Fi 區域網路連線',
        '// 請將 192.168.1.100 替換為電腦在 Wi-Fi 區域網路中的實際 IPv4 位址',
        'private const val BASE_URL = "http://192.168.1.100:8000/api/v1/"'
    ]))

    elements.append(build_h3_p('11-6-3 編譯建置與部署運行'))
    elements.append(build_normal_p('1. 執行單元契約測試：於終端機執行 ./gradlew testDebugUnitTest，確保 DiagnosisContractTest 11 項契約測試通過。', is_bullet=True))
    elements.append(build_normal_p('2. 直接安裝運行：將 Android 手機啟用 USB 偵錯連線電腦，於 Android Studio 點擊 Run app（Shift + F10）即可自動編譯並部署至裝置。', is_bullet=True))

    # 11-7 Web 管理後台存取與日常維護
    elements.append(build_h2_p('11-7 Web 管理後台存取與日常維護'))
    elements.append(build_h3_p('11-7-1 管理後台核心路由導覽'))
    elements.append(build_normal_p('管理者於瀏覽器登入具備 admin 權限之帳號後，可存取以下專業管理控制台：'))
    elements.append(build_normal_p('1. 管理者儀表板 (/dashboard)：展示全站植物診斷總筆數、常見病害排行榜、今日診斷活躍趨勢圖及系統健康指標。', is_bullet=True))
    elements.append(build_normal_p('2. 診斷回饋與審核介面 (/feedback)：審查農友回報之誤判個案（UC-13, UC-14），對照原 AI 診斷與農友修正標籤，作為主動學習重標註依據。', is_bullet=True))
    elements.append(build_normal_p('3. 使用者帳號管理介面 (/users)：查詢所有註冊會員清單、信箱驗證狀態，支援手動啟用帳號或調整權限角色。', is_bullet=True))
    elements.append(build_normal_p('4. Webcam 即時串流監控控制台 (/webcam)：瀏覽器即時影像監控介面，支援自訂畫面取樣頻率、自訂監控區域（ROI）及防抖警報門檻調試。', is_bullet=True))

    elements.append(build_h3_p('11-7-2 日常資料庫備份與知識庫更新'))
    elements.append(build_normal_p('定期備份 MySQL 資料庫，並在農業部釋出最新公開資料時執行熱更新：'))
    elements.append(build_code_p([
        '# 匯出資料庫備份',
        'mysqldump -u plant -p plant_db > backup_plant_db.sql',
        '',
        '# 執行農業部最新資料抓取與知識庫熱更新',
        'python update_reference_data.py',
        'python build_knowledge_base.py',
        'python seed.py'
    ]))

    elements.append(build_h3_p('11-7-3 團隊 Git 版本協作規範'))
    elements.append(build_normal_p('日常協作遵循原子化提交（Atomic Commit）原則，推播前先執行 git pull --rebase，嚴格保證手冊、代碼與資料庫遷移腳本對齊：'))
    elements.append(build_code_p([
        'git pull --rebase origin main',
        'git add path/to/changed_file.py',
        'git commit -m "feat/fix: 明確的變更說明"',
        'git push origin <feature-branch>'
    ]))

    return elements


def update_chapter_11_in_doc(docx_path):
    print(f"\n=======================================================")
    print(f"Processing Chapter 11 in: {docx_path}")
    if not os.path.exists(docx_path):
        print("  File not found! Skipping.")
        return False

    doc = docx.Document(docx_path)
    body_el = doc._body._element

    # Find Heading 1: 操作手冊 and Heading 1: 使用手冊
    start_idx = -1
    end_idx = -1
    for i, el in enumerate(body_el):
        if el.tag.endswith('}p'):
            t_txt = ''.join([n.text or '' for n in el.iter(qn('w:t'))]).strip()
            if t_txt == '操作手冊':
                start_idx = i
            elif start_idx != -1 and t_txt == '使用手冊':
                end_idx = i
                break

    if start_idx == -1 or end_idx == -1:
        print(f"  Could not find both 操作手冊 ({start_idx}) and 使用手冊 ({end_idx})!")
        return False

    print(f"  Found range: start={start_idx}, end={end_idx}. Elements between: {end_idx - start_idx - 1}")

    # Remove all elements between start_idx and end_idx
    elements_to_remove = [body_el[k] for k in range(start_idx + 1, end_idx)]
    for el in elements_to_remove:
        body_el.remove(el)

    print(f"  Removed {len(elements_to_remove)} existing elements between 操作手冊 and 使用手冊.")

    # Build and insert new Chapter 11 elements right after start_idx
    new_elements = build_chapter_11_elements()
    insert_pos = start_idx + 1
    for el in new_elements:
        body_el.insert(insert_pos, el)
        insert_pos += 1

    print(f"  Successfully inserted {len(new_elements)} structured elements for Chapter 11.")

    doc.save(docx_path)
    print(f"  Successfully saved: {docx_path}")
    return True


if __name__ == '__main__':
    target_files = [
        r'd:\plant_backend\documents\系統手冊_1.docx',
        r'd:\plant_backend\documents\系統手冊.docx',
        r'C:\Users\User\Downloads\系統手冊 (1).docx',
        r'C:\Users\User\Downloads\系統手冊.docx',
        r'C:\Users\User\OneDrive\文件\系統手冊.docx',
    ]
    for tf in target_files:
        try:
            update_chapter_11_in_doc(tf)
        except Exception as e:
            print(f"  Error on {tf}: {e}")
            import traceback
            traceback.print_exc()
