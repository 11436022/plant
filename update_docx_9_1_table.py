import os
from xml.sax.saxutils import escape
import docx
from docx.oxml import parse_xml
from docx.oxml.ns import qn

HEADERS_9_1 = ['元件', '檔案', '功能']
COL_WIDTHS_9_1 = [1616, 2977, 4875]  # dxa, total = 9468 dxa

ROWS_9_1 = [
    [
        '應用程式入口',
        'app/main.py',
        '建立FastAPI實例、掛載靜態目錄、載入各模組路由，並於系統啟動時執行資料庫Schema修補與例外處理。'
    ],
    [
        '認證路由',
        'app/routers/auth.py',
        '處理使用者註冊、JWT權杖登入、個人資料取得、信箱驗證、忘記密碼與重設密碼流程。'
    ],
    [
        '日誌路由',
        'app/routers/diaries.py',
        '提供植物圖片上傳自動診斷、日誌儲存、分頁歷史清單查詢、單筆詳細資訊檢視、備註更新與刪除。'
    ],
    [
        '診斷回饋路由',
        'app/routers/feedback.py',
        '接收農友對AI判定之作物或病蟲害校正回饋，記錄錯誤標註資料以支援模型主動學習（Active Learning）。'
    ],
    [
        'AI診斷服務',
        'app/services/ai.py\napp/services/convnext.py\napp/services/rag.py',
        '依多層架構執行本地ConvNeXt深度學習快篩與Gemini 1.5多模態大模型兜底，並結合FAISS向量資料庫（RAG）檢索生成專業防治處置建議。'
    ],
    [
        '知識檢索服務',
        'app/services/knowledge.py',
        '查詢作物、病害與蟲害百科知識；關聯農業部圖庫開放資料，確保診斷處置措施具備可追溯資料來源。'
    ],
    [
        '檔案管理服務',
        'app/services/files.py',
        '生成安全隨機檔名、嚴格驗證圖片MIME類型與副檔名，並提供上傳圖檔之公開存取URL。'
    ],
    [
        '郵件通知服務',
        'app/services/email.py',
        '封裝SMTP非同步郵件傳輸協議，負責發送新用戶驗證信、密碼重設安全代碼，以及Webcam監控即時警報信件。'
    ],
    [
        'Webcam監控服務',
        'app/routers/webcam.py\napp/services/webcam.py',
        '接收串流影像影格、多區域偵測、滑動時間窗口連續共識判定、異常警報觸發、Email通知與警報確認已讀。'
    ],
    [
        'Android API服務',
        'PlantApiService.kt\nAuthInterceptor.kt',
        '以Retrofit封裝所有RESTful API呼叫，並透過OkHttp攔截器自動注入Bearer JWT Token與統一處理過期重導。'
    ],
    [
        'Android核心介面',
        '各Activity.kt（含Home, Upload, Result, History, Webcam等）',
        '提供農友登入註冊、即時拍照診斷、辨識結果呈現、自訂Webcam監控區域與排程、歷史日誌管理及個人設定介面。'
    ]
]


def build_table_9_1_element(headers, rows):
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
    for w in COL_WIDTHS_9_1:
        xml_parts.append(f'    <w:gridCol w:w="{w}"/>')
    xml_parts.append('  </w:tblGrid>')

    # Header Row
    xml_parts.append('  <w:tr>')
    xml_parts.append('    <w:trPr><w:cantSplit/><w:jc w:val="center"/></w:trPr>')
    for col_idx, (text, w) in enumerate(zip(headers, COL_WIDTHS_9_1)):
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
        for col_idx, (raw_text, w) in enumerate(zip(row_data, COL_WIDTHS_9_1)):
            align = 'center' if col_idx == 0 else 'left'
            xml_parts.append('    <w:tc>')
            xml_parts.append('      <w:tcPr>')
            xml_parts.append(f'        <w:tcW w:w="{w}" w:type="dxa"/>')
            xml_parts.append('        <w:vAlign w:val="center"/>')
            xml_parts.append('      </w:tcPr>')
            # Support multiple lines in a single cell if text has \n
            lines = raw_text.split('\n')
            for line in lines:
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
                xml_parts.append(f'          <w:t>{escape(line)}</w:t>')
                xml_parts.append('        </w:r>')
                xml_parts.append('      </w:p>')
            xml_parts.append('    </w:tc>')
        xml_parts.append('  </w:tr>')

    xml_parts.append('</w:tbl>')
    return parse_xml(''.join(xml_parts))


def update_table_9_1_in_doc(docx_path):
    print(f"\nProcessing Table 9-1-1 in: {docx_path}")
    if not os.path.exists(docx_path):
        print("  File not found! Skipping.")
        return False

    doc = docx.Document(docx_path)
    body_el = doc._body._element

    # Find Table 9-1-1
    target_table = None
    for el in body_el:
        if el.tag.endswith('}tbl'):
            # check if header has '元件' and '檔案'
            cells_txt = []
            for tc in el.iter(qn('w:tc')):
                t_val = ''.join([n.text or '' for n in tc.iter(qn('w:t'))]).strip()
                cells_txt.append(t_val)
                if len(cells_txt) >= 3:
                    break
            if len(cells_txt) >= 3 and cells_txt[0] == '元件' and cells_txt[1] == '檔案':
                target_table = el
                break

    if target_table is None:
        print("  Table 9-1-1 not found in document!")
        return False

    new_tbl = build_table_9_1_element(HEADERS_9_1, ROWS_9_1)
    target_table.getparent().replace(target_table, new_tbl)
    doc.save(docx_path)
    print(f"  Successfully updated Table 9-1-1 ({len(ROWS_9_1)} rows) in {docx_path}")
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
            update_table_9_1_in_doc(tf)
        except Exception as e:
            print(f"  Error: {e}")
            import traceback
            traceback.print_exc()
