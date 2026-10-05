import copy
import os
from xml.sax.saxutils import escape
import docx
from docx.oxml import parse_xml
from docx.oxml.ns import qn

HEADERS_9_2 = ['類別', '元件 / 檔案名稱', '規格描述與功能職責']
COL_WIDTHS_9_2 = [2200, 2600, 4668]  # dxa, total = 9468 dxa

ROWS_9_2 = [
    [
        '容器部署與環境配置',
        'Dockerfile',
        '基於 Python 3.11-slim 輕量鏡像建構，整合 OpenMP（FAISS 必需）、虛擬環境隔離與非 root 安全使用者執行環境。'
    ],
    [
        '容器部署與環境配置',
        'docker-compose.yml',
        '定義後端服務與端口映射（8000:8000）、掛載持久化目錄、配置重啟策略與跨主機通訊網路（host-gateway）。'
    ],
    [
        '容器部署與環境配置',
        '.env / .env.example',
        '集中管理資料庫連線（DB）、JWT 加密金鑰、Gemini API Key、SMTP 郵箱憑證、Webcam 警報門檻與 CWA 氣象金鑰。'
    ],
    [
        '容器部署與環境配置',
        'requirements.txt',
        '規範後端 Python 套件版本（包含 FastAPI, PyTorch, FAISS-CPU, SQLAlchemy, Pydantic, google-genai 等）。'
    ],
    [
        '資料庫遷移與初始腳本',
        'init_db.sql',
        '初始化資料庫結構，預載基礎作物（crop）、病害（disease）與蟲害（pests）圖庫知識庫種子資料。'
    ],
    [
        '資料庫遷移與初始腳本',
        'alembic.ini 及 alembic/versions/',
        'Alembic 資料庫版本控制遷移腳本，記錄資料庫歷史演進並支援平滑熱修補（如 feedback、webcam_alert 等欄位更新）。'
    ],
    [
        'AI 模型權重與向量資產',
        'convnext_plant_best.pth',
        '本地端 PyTorch 輕量化 ConvNeXt-Tiny 深度學習模型訓練權重，提供毫秒級作物病蟲害邊緣快篩辨識能力。'
    ],
    [
        'AI 模型權重與向量資產',
        'idx_to_class.json',
        '模型預測輸出類別索引（Index）與中文作物病蟲害標準名稱之雙向映射字典。'
    ],
    [
        'AI 模型權重與向量資產',
        'knowledge_base.faiss',
        'FAISS 密集向量索引庫，儲存農業知識條目特徵向量，支援語意相似度檢索以實現 RAG 增強生成。'
    ],
    [
        'AI 模型權重與向量資產',
        'knowledge_content.json',
        '農業部開放資料與專家知識庫對應文本庫，提供檢索命中文獻之處置建議與可追溯出處。'
    ],
    [
        'Web 管理後台模板',
        'templates/dashboard.html',
        '系統管理總覽儀表板，提供診斷日誌統計圖表、警報狀態監控與伺服器健康狀況。'
    ],
    [
        'Web 管理後台模板',
        'templates/feedback.html',
        '使用者回饋與主動學習標註審核頁面，供專家審視農友回報的誤判快照並納入微調數據集。'
    ],
    [
        'Web 管理後台模板',
        'templates/users.html',
        '使用者帳號管理頁面，支援管理者查詢會員清單、信箱驗證狀態與權限角色調整。'
    ],
    [
        'Web 管理後台模板',
        'templates/webcam.html',
        'Webcam 即時串流監控調試介面，提供自訂檢驗區域與排程測試。'
    ],
    [
        '靜態資源與持久化目錄',
        'static/uploads/',
        '持久化儲存使用者拍照上傳的植物診斷快照圖檔。'
    ],
    [
        '靜態資源與持久化目錄',
        'static/feedback_uploads/',
        '持久化儲存使用者回報誤判更正時所上傳之原始比對圖檔。'
    ],
    [
        '靜態資源與持久化目錄',
        'static/reset_password.html',
        '密碼重設前端靜態響應頁面，接收信箱一次性權杖進行安全密碼更新。'
    ],
    [
        'Android 端配置與資源',
        'build.gradle.kts',
        '定義 Android 編譯版本（SDK 26~36）、ViewBinding、Retrofit2、CameraX、Glide 與各項第三方支援庫依賴。'
    ],
    [
        'Android 端配置與資源',
        'res/layout/ 及 res/drawable/',
        '包含所有 Activity/Dialog XML 版面設計檔、向量圖示、圓角卡片背景與診斷狀態視覺化標籤樣式。'
    ]
]


def build_table_9_2_element(headers, rows):
    """Constructs a clean 3-column Word table XML element matching original styling."""
    xml_parts = [
        '<w:tbl xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">',
        '  <w:tblPr>',
        '    <w:tblStyle w:val="aff2"/>',
        '    <w:tblW w:w="9468" w:type="dxa"/>',
        '    <w:jc w:val="center"/>',
        '    <w:tblLook w:val="04A0" w:firstRow="1" w:lastRow="0" w:firstColumn="1" w:lastColumn="0" w:noHBand="0" w:noVBand="1"/>',
        '  </w:tblPr>',
        '  <w:tblGrid>'
    ]
    for w in COL_WIDTHS_9_2:
        xml_parts.append(f'    <w:gridCol w:w="{w}"/>')
    xml_parts.append('  </w:tblGrid>')

    # Header Row
    xml_parts.append('  <w:tr>')
    xml_parts.append('    <w:trPr><w:cantSplit/><w:jc w:val="center"/></w:trPr>')
    for col_idx, (text, w) in enumerate(zip(headers, COL_WIDTHS_9_2)):
        xml_parts.append('    <w:tc>')
        xml_parts.append('      <w:tcPr>')
        xml_parts.append(f'        <w:tcW w:w="{w}" w:type="dxa"/>')
        xml_parts.append('        <w:shd w:val="clear" w:color="auto" w:fill="DDEAD7"/>')
        xml_parts.append('        <w:vAlign w:val="center"/>')
        xml_parts.append('      </w:tcPr>')
        xml_parts.append('      <w:p>')
        xml_parts.append('        <w:pPr>')
        xml_parts.append('          <w:ind w:leftChars="0" w:left="0" w:rightChars="0" w:right="0"/>')
        xml_parts.append('          <w:jc w:val="center"/>')
        xml_parts.append('          <w:rPr>')
        xml_parts.append('            <w:rFonts w:hint="eastAsia"/>')
        xml_parts.append('            <w:lang w:eastAsia="zh-TW"/>')
        xml_parts.append('          </w:rPr>')
        xml_parts.append('        </w:pPr>')
        xml_parts.append('        <w:r>')
        xml_parts.append('          <w:rPr>')
        xml_parts.append('            <w:rFonts w:ascii="Calibri" w:hAnsi="Calibri" w:eastAsia="微軟正黑體"/>')
        xml_parts.append('            <w:b/>')
        xml_parts.append('            <w:sz w:val="21"/>')
        xml_parts.append('            <w:szCs w:val="21"/>')
        xml_parts.append('            <w:lang w:eastAsia="zh-TW"/>')
        xml_parts.append('          </w:rPr>')
        xml_parts.append(f'          <w:t>{escape(text)}</w:t>')
        xml_parts.append('        </w:r>')
        xml_parts.append('      </w:p>')
        xml_parts.append('    </w:tc>')
    xml_parts.append('  </w:tr>')

    # Data Rows
    for r_idx, row_data in enumerate(rows):
        xml_parts.append('  <w:tr>')
        xml_parts.append('    <w:trPr><w:cantSplit/><w:jc w:val="center"/></w:trPr>')
        for col_idx, (text, w) in enumerate(zip(row_data, COL_WIDTHS_9_2)):
            align = 'center' if col_idx == 0 else 'left'
            xml_parts.append('    <w:tc>')
            xml_parts.append('      <w:tcPr>')
            xml_parts.append(f'        <w:tcW w:w="{w}" w:type="dxa"/>')
            xml_parts.append('        <w:vAlign w:val="center"/>')
            xml_parts.append('      </w:tcPr>')
            xml_parts.append('      <w:p>')
            xml_parts.append('        <w:pPr>')
            xml_parts.append('          <w:ind w:leftChars="0" w:left="0" w:rightChars="0" w:right="0"/>')
            xml_parts.append(f'          <w:jc w:val="{align}"/>')
            xml_parts.append('          <w:rPr>')
            xml_parts.append('            <w:rFonts w:hint="eastAsia"/>')
            xml_parts.append('            <w:lang w:eastAsia="zh-TW"/>')
            xml_parts.append('          </w:rPr>')
            xml_parts.append('        </w:pPr>')
            xml_parts.append('        <w:r>')
            xml_parts.append('          <w:rPr>')
            xml_parts.append('            <w:rFonts w:ascii="Calibri" w:hAnsi="Calibri" w:eastAsia="微軟正黑體"/>')
            xml_parts.append('            <w:sz w:val="21"/>')
            xml_parts.append('            <w:szCs w:val="21"/>')
            xml_parts.append('            <w:lang w:eastAsia="zh-TW"/>')
            xml_parts.append('          </w:rPr>')
            xml_parts.append(f'          <w:t>{escape(text)}</w:t>')
            xml_parts.append('        </w:r>')
            xml_parts.append('      </w:p>')
            xml_parts.append('    </w:tc>')
        xml_parts.append('  </w:tr>')

    xml_parts.append('</w:tbl>')
    return parse_xml(''.join(xml_parts))


def build_caption_9_2_element():
    """Builds the Caption paragraph element for 表 9-2-1."""
    xml = """<w:p xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:pPr>
    <w:pStyle w:val="af7"/>
    <w:keepNext/>
    <w:ind w:left="280" w:right="280"/>
    <w:jc w:val="center"/>
    <w:rPr>
      <w:color w:val="000000"/>
      <w:sz w:val="28"/>
      <w:szCs w:val="28"/>
      <w:lang w:eastAsia="zh-TW"/>
    </w:rPr>
  </w:pPr>
  <w:r>
    <w:rPr>
      <w:rFonts w:ascii="微軟正黑體" w:hAnsi="微軟正黑體" w:eastAsia="微軟正黑體"/>
      <w:color w:val="000000"/>
      <w:sz w:val="28"/>
      <w:szCs w:val="28"/>
      <w:lang w:eastAsia="zh-TW"/>
    </w:rPr>
    <w:t>表 9-2-1 附屬元件與依附項目清單</w:t>
  </w:r>
</w:p>"""
    return parse_xml(xml)


def build_empty_p():
    """Builds a single blank line paragraph."""
    xml = """<w:p xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:pPr>
    <w:pStyle w:val="af7"/>
    <w:ind w:left="280" w:right="280"/>
    <w:rPr><w:lang w:eastAsia="zh-TW"/></w:rPr>
  </w:pPr>
</w:p>"""
    return parse_xml(xml)


def update_section_9_2_in_doc(docx_path):
    print(f"\n=======================================================")
    print(f"Processing Section 9-2 in: {docx_path}")
    if not os.path.exists(docx_path):
        print("  File not found! Skipping.")
        return False

    doc = docx.Document(docx_path)
    body_el = doc._body._element

    # 1. Update Table of Tables (表目錄)
    p911_toc = None
    has_921_toc = False
    for el in body_el:
        if el.tag.endswith('}p'):
            t_txt = ''.join([n.text or '' for n in el.iter(qn('w:t'))])
            has_tab = '\t' in t_txt or any(n.tag.endswith('}tab') for n in el.iter())
            if has_tab:
                if '9-2-1' in t_txt or '附屬元件' in t_txt:
                    has_921_toc = True
                if '9-1-1' in t_txt or ('9-1' in t_txt and '元件清單' in t_txt):
                    p911_toc = el

    if p911_toc is not None and not has_921_toc:
        print("  Adding 表 9-2-1 into Table of Tables (表目錄)...")
        clone_921 = copy.deepcopy(p911_toc)
        for tn in clone_921.iter(qn('w:t')):
            if tn.text and ('9-1-1' in tn.text or '9-1' in tn.text):
                tn.text = tn.text.replace('9-1-1', '9-2-1').replace('9-1', '9-2-1')
            elif tn.text and '元件清單及規格描述' in tn.text:
                tn.text = tn.text.replace('元件清單及規格描述', '附屬元件與依附項目清單')
        p_parent = p911_toc.getparent()
        p_parent.insert(p_parent.index(p911_toc) + 1, clone_921)
        print("  Successfully added 表 9-2-1 to 表目錄.")

    # 2. Check if Table 9-2-1 already exists in body
    has_table_9_2 = False
    for el in body_el:
        if el.tag.endswith('}tbl'):
            cells_txt = []
            for tc in el.iter(qn('w:tc')):
                cells_txt.append(''.join([n.text or '' for n in tc.iter(qn('w:t'))]).strip())
                if len(cells_txt) >= 3:
                    break
            if len(cells_txt) >= 3 and cells_txt[0] == '類別' and '檔案' in cells_txt[1]:
                has_table_9_2 = True
                break

    # Find the paragraph mentioning Dockerfile
    docker_para = None
    for i, el in enumerate(body_el):
        if el.tag.endswith('}p'):
            t_txt = ''.join([n.text or '' for n in el.iter(qn('w:t'))])
            if 'Dockerfile' in t_txt and ('附屬元件' in t_txt or '依附' in t_txt or '本系統除核心' in t_txt):
                docker_para = el
            elif '本系統除核心程式模組外' in t_txt:
                docker_para = el

    if docker_para is not None:
        intro_text = '本系統除核心程式模組外，亦包含各項附屬之依附性軟體、容器化配置、資料庫遷移腳本、AI模型與向量索引資產、Web管理後台模板及Android端資源，整體清單如表 9-2-1 所示。'
        t_nodes = list(docker_para.iter(qn('w:t')))
        if t_nodes:
            t_nodes[0].text = intro_text
            for tn in t_nodes[1:]:
                tn.text = ''
        print("  Updated 9-2 introduction paragraph.")

        if not has_table_9_2:
            parent = docker_para.getparent()
            idx = parent.index(docker_para)
            caption_el = build_caption_9_2_element()
            table_el = build_table_9_2_element(HEADERS_9_2, ROWS_9_2)
            parent.insert(idx + 1, caption_el)
            parent.insert(idx + 2, table_el)
            parent.insert(idx + 3, build_empty_p())
            print(f"  Inserted 表 9-2-1 caption and table ({len(ROWS_9_2)} rows).")
        else:
            print("  Table 9-2-1 already present in body.")

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
            update_section_9_2_in_doc(tf)
        except Exception as e:
            print(f"  Error: {e}")
            import traceback
            traceback.print_exc()
