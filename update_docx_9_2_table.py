import copy
import os
from xml.sax.saxutils import escape
import docx
from docx.oxml import parse_xml
from docx.oxml.ns import qn

HEADERS_9_2 = ['類別', '元件 / 檔案', '規格描述與功能職責']
COL_WIDTHS_9_2 = [2200, 2600, 4668]  # dxa, total = 9468 dxa

ROWS_9_2 = [
    [
        '容器部署環境',
        'Dockerfile、docker-compose.yml',
        '封裝 Python 3.11 輕量化執行環境與非 root 安全使用者，提供後端與資料庫服務之一鍵容器化部署與網路映射。'
    ],
    [
        '環境組態設定',
        '.env.example',
        '集中規範系統全域環境變數範本，包含資料庫連線、JWT 金鑰、Gemini API Key、SMTP 憑證與氣象開放資料設定。'
    ],
    [
        '套件依賴管理',
        'requirements.txt、build.gradle.kts',
        '嚴格規範後端 Python（FastAPI, PyTorch, FAISS）與 Android 端（Retrofit, CameraX, Glide）之相依函式庫與版本。'
    ],
    [
        '資料庫遷移工具',
        'init_db.sql、alembic/',
        '提供系統首次安裝的基礎結構與農業百科種子資料建置，並透過 Alembic 腳本支援資料庫版本的平滑演進與熱修補。'
    ],
    [
        '本地 AI 快篩模型',
        'convnext_plant_best.pth、idx_to_class.json',
        '包含本地端 PyTorch ConvNeXt-Tiny 卷積神經網路訓練權重與類別雙向映射表，提供毫秒級即時病害邊緣快篩。'
    ],
    [
        'RAG 向量檢索資產',
        'knowledge_base.faiss、knowledge_content.json',
        '整合 FAISS 密集特徵向量索引庫與農業部文獻文本庫，支援語意相似度檢索以生成專業可追溯之防治建議。'
    ],
    [
        '後台模板與靜態存儲',
        'templates/*.html、static/uploads/',
        '提供管理者儀表板、使用者回饋審查網頁模板，以及使用者植物診斷快照圖檔之持久化儲存目錄。'
    ],
    [
        'Android 介面資源',
        'res/layout/、res/drawable/',
        '定義 Android 前端所有 Activity 與 Dialog 之 XML 版面佈局、自訂互動監控框、向量圖示與狀態標籤樣式。'
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


def update_table_9_2_to_core8(docx_path):
    print(f"\n=======================================================")
    print(f"Streamlining Table 9-2-1 in: {docx_path}")
    if not os.path.exists(docx_path):
        print("  File not found! Skipping.")
        return False

    doc = docx.Document(docx_path)
    body_el = doc._body._element

    # Find Table 9-2-1
    target_table = None
    for el in body_el:
        if el.tag.endswith('}tbl'):
            cells_txt = []
            for tc in el.iter(qn('w:tc')):
                cells_txt.append(''.join([n.text or '' for n in tc.iter(qn('w:t'))]).strip())
                if len(cells_txt) >= 3:
                    break
            if len(cells_txt) >= 3 and cells_txt[0] == '類別' and '檔案' in cells_txt[1]:
                target_table = el
                break

    if target_table is not None:
        new_tbl = build_table_9_2_element(HEADERS_9_2, ROWS_9_2)
        target_table.getparent().replace(target_table, new_tbl)
        doc.save(docx_path)
        print(f"  Successfully updated Table 9-2-1 to 8 core items in {docx_path}")
        return True
    else:
        print(f"  Table 9-2-1 not found in {docx_path}!")
        return False


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
            update_table_9_2_to_core8(tf)
        except Exception as e:
            print(f"  Error: {e}")
            import traceback
            traceback.print_exc()
