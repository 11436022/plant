import os
import sys
import re
from xml.sax.saxutils import escape
import docx
from docx.oxml import parse_xml
from docx.oxml.ns import qn

sys.stdout.reconfigure(encoding='utf-8')


def build_h2_p(text):
    """Clean Heading 2 paragraph: uses style 21 without direct font/size overrides,
    stripping hardcoded '12-X ' prefix so Word's automatic numbering produces clean '12-X '."""
    clean_text = re.sub(r'^12-\d+\s*', '', text)
    xml = f"""<w:p xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:pPr>
    <w:pStyle w:val="21"/>
    <w:keepNext/>
    <w:ind w:left="847" w:right="280"/>
    <w:spacing w:before="240" w:after="120"/>
    <w:rPr>
      <w:color w:val="auto"/>
      <w:lang w:eastAsia="zh-TW"/>
    </w:rPr>
  </w:pPr>
  <w:r>
    <w:rPr>
      <w:color w:val="auto"/>
      <w:lang w:eastAsia="zh-TW"/>
    </w:rPr>
    <w:t>{escape(clean_text)}</w:t>
  </w:r>
</w:p>"""
    return parse_xml(xml)


def build_h3_p(text):
    """Sub-heading 3: distinctive title styling with deep blue color."""
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
    """Standard body paragraph with proper Chinese typography."""
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


def build_bullet_p(text):
    return build_normal_p(text, indent_first_line=False, is_bullet=True)


def build_chapter_12_elements():
    """Generates all XML elements for Chapter 12 (使用手冊)."""
    elements = []

    # 12-1 狀態轉換圖概覽
    elements.append(build_h2_p('12-1 狀態轉換圖概覽'))
    elements.append(build_normal_p('本系統（智慧植物病蟲害辨識與健康管理系統）採用以使用者為核心之情境驅動設計，全系統操作流程可抽象化為一系列清晰、可預測之「狀態（State）」轉換。使用者在行動端應用程式（Android App）或 Web 管理介面上的每一個「觸控／點擊操作」均會觸發特定「事件（Event）」，並推動系統在不同「畫面狀態」之間安全轉移。'))
    elements.append(build_normal_p('系統之核心狀態機涵蓋以下六大核心畫面狀態：'))
    elements.append(build_bullet_p('1. 狀態 1：登入/註冊頁 (Unauthenticated State)：未認證初始狀態，負責使用者身分識別、信箱驗證與密碼安全。'))
    elements.append(build_bullet_p('2. 狀態 2：應用程式主頁 (Main Dashboard State)：已認證核心中樞，提供各項主要業務功能入口與系統連線狀態指示。'))
    elements.append(build_bullet_p('3. 狀態 3：歷史紀錄列表頁 (History List State)：個人專屬植物健康日誌總覽，以時間軸降冪展示所有過往診斷紀錄。'))
    elements.append(build_bullet_p('4. 狀態 4：歷史紀錄詳情頁 (History Detail State)：單筆病害深度查閱狀態，呈現高解析度病斑快照、AI 診斷標籤、官方農業防治指南與個人化備忘筆記。'))
    elements.append(build_bullet_p('5. 狀態 5：開始診斷/上傳頁 (Diagnosis Start/Upload State)：影像採集狀態，支援 CameraX 相機即時拍照對焦與本機相簿選圖。'))
    elements.append(build_bullet_p('6. 狀態 6：診斷結果頁 (Diagnosis Result State)：AI 多層級推論完成狀態，展示卷積快篩、Gemini 雲端辨析、三方仲裁結論、置信度與農業部文獻追溯依據。'))

    # 12-2 畫面流程與操作說明
    elements.append(build_h2_p('12-2 畫面流程與操作說明'))
    elements.append(build_normal_p('以下詳細定義各畫面狀態之進入條件、介面功能元件、可執行操作及狀態轉換契約：'))

    # 12-2-1 狀態 1
    elements.append(build_h3_p('12-2-1 狀態 1：登入與註冊頁 (Unauthenticated State)'))
    elements.append(build_bullet_p('• 進入條件：使用者首次啟動 Android App、或於主頁點擊「登出」、或本地 JWT Token 過期。'))
    elements.append(build_bullet_p('• 畫面功能：提供帳號密碼登入、新用戶註冊及忘記密碼入口。傳輸均經 TLS 加密通道，後端採用 Argon2id 演算法防護。'))
    elements.append(build_bullet_p('• 登入操作：輸入已完成信箱驗證之帳號密碼，點擊登入。驗證成功後安全儲存 Token 並轉換至「狀態 2：應用程式主頁」；若帳密錯誤則統一口徑提示「帳號或密碼錯誤」並停留在當前頁面。'))
    elements.append(build_bullet_p('• 註冊與啟用：填寫暱稱、信箱及密碼提交後，系統發送啟用驗證信。農友須至信箱點擊連結完成驗證方可正式登入。'))
    elements.append(build_bullet_p('• 忘記密碼：輸入註冊信箱，後端生成具 15 分鐘時效之單次安全權杖並寄送重設郵件。'))

    # 12-2-2 狀態 2
    elements.append(build_h3_p('12-2-2 狀態 2：應用程式主頁 (Main Dashboard State)'))
    elements.append(build_bullet_p('• 進入條件：使用者通過身分鑑權成功登入，或自其他子頁面點擊「返回主頁」。'))
    elements.append(build_bullet_p('• 畫面元件：頂部導覽列展示使用者暱稱與伺服器連線狀態指示燈；核心區域提供「📸 即時病害診斷」、「📖 植物健康日誌」及「🔍 農業百科知識庫」導航大卡片。'))
    elements.append(build_bullet_p('• 核心操作：點擊「📸 即時病害診斷」按鈕轉換至「狀態 5：開始診斷/上傳頁」；點擊「📖 植物健康日誌」按鈕轉換至「狀態 3：歷史紀錄列表頁」；點擊「登出」則清除本機 Token 轉換至「狀態 1」。'))

    # 12-2-3 狀態 3
    elements.append(build_h3_p('12-2-3 狀態 3：歷史紀錄列表頁 (History List State)'))
    elements.append(build_bullet_p('• 進入條件：於主頁點擊「植物健康日誌」，或於紀錄詳情頁點擊返回。'))
    elements.append(build_bullet_p('• 畫面功能：採用 RecyclerView 結構，依診斷建立時間降冪排序。每張卡片展示病斑縮圖、作物類別、確診病害名稱、時間戳記及狀態標籤（健康、確診或需專家複核）。支援下拉手勢（Swipe-to-Refresh）即時同步伺服器最新數據。'))
    elements.append(build_bullet_p('• 操作轉換：點擊任一病害卡片帶入 UUID 轉換至「狀態 4：歷史紀錄詳情頁」；點擊頂部返回按鈕返回「狀態 2：應用程式主頁」。'))

    # 12-2-4 狀態 4
    elements.append(build_h3_p('12-2-4 狀態 4：歷史紀錄詳情頁 (History Detail State)'))
    elements.append(build_bullet_p('• 進入條件：於歷史清單點擊特定病害紀錄進入。'))
    elements.append(build_bullet_p('• 畫面功能：支援手勢雙指縮放檢視原始高解析度病斑照片；完整展示 AI 診斷標籤、置信度進度條、三方仲裁決策註記及農業部官方防治處方指南（含可追溯文獻引用）。'))
    elements.append(build_bullet_p('• 備忘與管理 (UC-08)：提供農友輸入欄記錄實體用藥進度與病情追蹤筆記；點擊「儲存筆記」即時更新；點擊「刪除」經二次確認後自雲端移除並返回「狀態 3」。'))

    # 12-2-5 狀態 5
    elements.append(build_h3_p('12-2-5 狀態 5：開始診斷/上傳頁 (Diagnosis Start/Upload State)'))
    elements.append(build_bullet_p('• 進入條件：於主頁點擊「📸 即時病害診斷」。'))
    elements.append(build_bullet_p('• 畫面功能：提供「啟動相機拍攝（CameraX 自動對焦與中心十字輔助框）」與「從相簿選取照片」雙模式。選取後即時於預覽窗格呈現，並提供拍攝規範提示（充足光線、聚焦葉片、避免雜草）。'))
    elements.append(build_bullet_p('• 操作轉換：確認清晰後點擊「開始 AI 智慧診斷」，系統顯示半透明載入動畫並發送 Multipart 表單至後端，分析完成後自動轉換至「狀態 6：診斷結果頁」；點擊取消則返回「狀態 2」。'))

    # 12-2-6 狀態 6
    elements.append(build_h3_p('12-2-6 狀態 6：診斷結果頁 (Diagnosis Result State)'))
    elements.append(build_bullet_p('• 進入條件：影像上傳後經雙層 AI 與三方仲裁器推論完成並回傳。'))
    elements.append(build_bullet_p('• 畫面功能：清晰呈現中英文病害名稱、信心指數儀表（0%~100%）、推論來源標籤（ConvNeXt 高速快篩或 Gemini 專家多模態）及農業部 RAG 官方防治指引。'))
    elements.append(build_bullet_p('• 安全與日誌儲存：提供法律免責聲明。農友可輸入備忘記事後點擊「儲存至植物日誌」完成持久化保存並返回主頁；若判定結果有疑義，可點擊「回報診斷異常」上傳正確真值協助模型進化。'))

    # 12-3 核心功能情境操作與展示腳本
    elements.append(build_h2_p('12-3 核心功能情境操作與展示腳本'))
    elements.append(build_normal_p('為確保評審委員會及系統使用者能迅速驗證各項功能之可靠性與健壯性，本手冊制定三大核心情境驗證腳本：'))

    # 12-3-1
    elements.append(build_h3_p('12-3-1 情境一：標準端到端病害診斷流程'))
    elements.append(build_bullet_p('• 展示目的：驗證農友自登入、拍照、雙模型快篩辨析至日誌存檔之完整工作流程。'))
    elements.append(build_bullet_p('• 操作步驟：1. 開啟 App 登入；2. 點擊「即時病害診斷」並拍攝番茄早疫病葉片；3. 點擊「開始 AI 智慧診斷」；4. 系統於 1 秒內回傳診斷結果（番茄早疫病，信心度 96.8%）；5. 閱讀農業部防治指引並輸入備忘筆記「已噴灑波爾多液」；6. 點擊確認存檔，返回主頁進入日誌確認該筆紀錄置頂。'))
    elements.append(build_bullet_p('• 查核證據：後端回傳 HTTP 200，MySQL plant_diary 表成功新增記錄，圖檔儲存於 static/uploads/。'))

    # 12-3-2
    elements.append(build_h3_p('12-3-2 情境二：低信心爭議病斑與域外作物 (OOD) 處置展示'))
    elements.append(build_bullet_p('• 展示目的：驗證三方仲裁器防幻覺機制與安全降級保護。'))
    elements.append(build_bullet_p('• 操作步驟：1. 於診斷頁面上傳未支援之域外作物（如草莓）或模糊病斑；2. 本地卷積模型信心度不足，自動啟動第二層雲端 Gemini 多模態深度分析；3. 三方仲裁器判定特徵不合，主動拒絕武斷定論，回傳「無法明確判定（Unknown）／建議採樣送檢」；4. 畫面呈現黃色警告標籤並引導使用者重新取樣。'))
    elements.append(build_bullet_p('• 查核證據：仲裁器記錄 OOD 救援日誌，系統不產生偽陰性或高信心誤判。'))

    # 12-3-3
    elements.append(build_h3_p('12-3-3 情境三：Webcam 智慧監控串流與連續異常自動警報'))
    elements.append(build_bullet_p('• 展示目的：驗證即時監控連續 3 幀防抖共識與非同步郵件警報架構。'))
    elements.append(build_bullet_p('• 操作步驟：1. 啟動 Webcam 監控工作階段；2. 將健康植株置於鏡頭前，連續異常計數（Streak）維持為 0；3. 移入受感染植株，系統逐幀計數（Streak: 1 -> 2 -> 3）；4. 達成連續 3 幀共識後觸發警報事務，儲存異常快照並非同步發送緊急預警信至農友信箱。'))
    elements.append(build_bullet_p('• 查核證據：農友電子信箱即時收到「植物健康警報通知」郵件附帶快照，系統日誌無阻塞。'))

    # 12-4 Web 管理者後台日常維運使用指南
    elements.append(build_h2_p('12-4 Web 管理者後台日常維運使用指南'))
    elements.append(build_normal_p('針對農場技術管理員，系統提供專屬之 Web 營運後台，支援全域監控與資料維護：'))

    # 12-4-1
    elements.append(build_h3_p('12-4-1 管理者登入與權限鑑權'))
    elements.append(build_bullet_p('• 存取路徑：瀏覽器存取 http://<伺服器IP>:8000/admin/login。輸入管理員帳密（is_admin=True）登入，系統簽發 HttpOnly Cookie 保護連線，非管理員帳號自動阻擋。'))

    # 12-4-2
    elements.append(build_h3_p('12-4-2 管理儀表板與全域監控'))
    elements.append(build_bullet_p('• 核心功能：圖表化呈現每日診斷總量、作物病害分佈佔比圓餅圖、高風險疫情警示、後端伺服器資源負載及 PyTorch 模型平均推論延遲時間。'))

    # 12-4-3
    elements.append(build_h3_p('12-4-3 使用者糾錯回饋審查與模型進化'))
    elements.append(build_bullet_p('• 核心功能：審查農友透過 App 提報之誤判回饋，比對原始影像與農友修正標籤。管理者核准後可一鍵「納入重訓樣本庫」，自動打包入微調資料集推動模型持續迭代。'))

    # 12-4-4
    elements.append(build_h3_p('12-4-4 資料庫備份與知識庫更新操作'))
    elements.append(build_bullet_p('• 日常備份：支援於後台一鍵觸發 MySQL 邏輯熱備份，自動生成時間戳快照檔案並妥善歸檔。'))
    elements.append(build_bullet_p('• 知識庫熱更新：當農業部發布最新專書時，上傳更新之 data.json 點擊「重建向量索引」，系統背景無縫熱更新 FAISS 向量庫，無需重啟伺服器服務。'))

    return elements


def update_chapter_12_in_doc(docx_path):
    print(f"\n=======================================================")
    print(f"Processing Chapter 12 in: {docx_path}")
    if not os.path.exists(docx_path):
        print("  File not found! Skipping.")
        return False

    doc = docx.Document(docx_path)
    body_el = doc._body._element

    # Find Heading 1: 使用手冊 and Heading 1: 感想 (or 第13章)
    start_idx = -1
    end_idx = -1
    for i, el in enumerate(body_el):
        if el.tag.endswith('}p'):
            t_txt = ''.join([n.text or '' for n in el.iter(qn('w:t'))]).strip()
            if '使用手冊' in t_txt and ('第12章' in t_txt or '第 12 章' in t_txt or t_txt == '使用手冊'):
                start_idx = i
            elif start_idx != -1 and ('感想' in t_txt or '第13章' in t_txt or '第 13 章' in t_txt):
                end_idx = i
                break

    if start_idx == -1 or end_idx == -1:
        print(f"  Could not find both 使用手冊 ({start_idx}) and 感想 ({end_idx})!")
        return False

    print(f"  Found range: start={start_idx}, end={end_idx}. Elements between: {end_idx - start_idx - 1}")

    # Remove all elements between start_idx and end_idx
    elements_to_remove = [body_el[k] for k in range(start_idx + 1, end_idx)]
    for el in elements_to_remove:
        body_el.remove(el)

    print(f"  Removed {len(elements_to_remove)} existing elements between 使用手冊 and 感想.")

    # Build and insert new Chapter 12 elements right after start_idx
    new_elements = build_chapter_12_elements()
    insert_pos = start_idx + 1
    for el in new_elements:
        body_el.insert(insert_pos, el)
        insert_pos += 1

    print(f"  Successfully inserted {len(new_elements)} structured elements for Chapter 12.")

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
            update_chapter_12_in_doc(tf)
        except Exception as e:
            print(f"  Error on {tf}: {e}")
            import traceback
            traceback.print_exc()
