import copy
import os
import sys
from xml.sax.saxutils import escape
import docx
from docx.oxml import parse_xml
from docx.oxml.ns import qn

sys.stdout.reconfigure(encoding='utf-8')

HEADERS_10_1 = ['測試類型', '測試方式', '目標']
COL_WIDTHS_10_1 = [1984, 3969, 3515]  # dxa, total = 9468 dxa

ROWS_10_1 = [
    [
        '單元測試',
        '密碼安全與資料校驗：\n1. 執行密碼雜湊與比對驗證（Argon2 / Bcrypt）。\n2. 驗證單次驗證 Token 雜湊函式（SHA-256）產出。\n3. 農業知識庫種子資料匯入與去重邏輯測試。',
        '1. 密碼單向雜湊不可逆，校驗邏輯正確無誤。\n2. Token 雜湊具唯一性與固定長度，符合資安標準。\n3. 資料庫參考資料支援冪等更新，不重複寫入。'
    ],
    [
        'AI 階層與仲裁測試',
        'ConvNeXt 快篩、Gemini 雲端診斷與三方仲裁器：\n1. 檢驗本地 ConvNeXt 權重載入與標籤雙向映射。\n2. 測試高信心直接命中與低信心降級至雲端流程。\n3. 驗證雙中同判定、域外作物 (OOD) 剔除、反向救援與病斑衝突仲裁。\n4. 驗證防幻覺地面真值（Database Grounding）白名單替換。',
        '1. 本地模型推論正常，高信心快篩無縫響應。\n2. 仲裁器精準處理跨模型衝突，有效剔除未知作物。\n3. 非官方核准之虛構病害名自動攔截，強制使用農業部專家文獻建議。'
    ],
    [
        '即時監控測試',
        '視訊監控、防抖共識與警報機制：\n1. 畫面幀品質檢驗（過小、全黑、無細節圖過濾）。\n2. 連續判定共識（Temporal Consensus）模擬。\n3. 冷卻時間（Cooldown）與 Session/Region 範圍防串擾。\n4. 警報資料庫寫入與 SMTP 寄信非同步隔離測試。',
        '1. 無效畫面直接拒絕，避免浪費伺服器推論資源。\n2. 必須連續 3 幀判定為相同異常且具地面真值才觸發警報。\n3. 冷卻期內不重複發信，監控會話隔離完整。\n4. 即使郵件寄送失敗，警報紀錄與快照圖片仍持久化保存。'
    ],
    [
        '向量檢索測試',
        'FAISS 向量知識庫與檢索完整性：\n1. 實體 FAISS 索引載入、向量比對與文字檢索。\n2. 清單雜湊（SHA256）與向量維度校驗。\n3. 模擬清單損毀或索引缺失情境。',
        '1. 檢索正確回傳語意最相近之農業病害防治指南。\n2. 檔案竄改或維度不符時主動拒絕載入。\n3. 索引缺失時自動觸發安全降級，保證 API 服務不中斷。'
    ],
    [
        '介面契約測試',
        'Android 前端與後端 DTO 雙向相容：\n1. 前端 DiagnosisContractTest 單元契約測試。\n2. 診斷回傳 JSON 序列化與欄位保留測試。\n3. 使用者修正備忘與原始 AI 診斷欄位隔離。\n4. 數值邊界（NaN、Inf、極端值）與免責聲明檢驗。',
        '1. 前後端資料結構契約一致，無欄位遺失。\n2. 儲存時保留原始 AI 診斷，不被使用者筆記覆蓋。\n3. 信心值明確標註「非準確率且非專家審核」，舊版缺少欄位時安全降級不閃退。'
    ],
    [
        '安全與權限測試',
        '使用者認證、存取控制與防越權機制：\n1. 未驗證信箱存取受保護端點阻擋。\n2. 錯誤密碼與未註冊帳號統一回應（防帳號探測）。\n3. 跨使用者存取隔離（IDOR 漏洞防範）。\n4. 診斷暫存過期（TTL）與重複確認防護。\n5. 管理者專屬儀表板與回饋審核端點權限阻擋。',
        '1. 未驗證帳號回傳 403 / 401 拒絕存取。\n2. 登入失敗統一口徑，不洩漏帳號是否存在。\n3. 任何使用者無法確認或刪除他人之診斷紀錄。\n4. 過期暫存自動作廢，重複確認回傳錯誤。\n5. 非管理者存取管理端點直接阻擋。'
    ],
    [
        '功能與整合測試',
        '端到端業務流程與資料庫遷移：\n1. 完整流程：註冊 → 信箱發信/驗證 → 登入 → 拍照上傳 → AI 診斷 → 確認入庫 → 歷史查看/備忘編輯 → 登出。\n2. Alembic 資料庫版本遷移（升級與降級）。',
        '1. 全流程資料流傳遞正常，各階段資料庫寫入正確。\n2. 圖片檔案正確保存於持久化儲存區。\n3. Alembic 資料庫 Schema 遷移無分支衝突。'
    ],
    [
        '效能與可靠度測試',
        'API 延遲指標與高負載穩定度：\n1. 本地 ConvNeXt-Tiny 推論延遲量測。\n2. 雲端 Gemini + RAG 綜合推論耗時量測。\n3. 自動化測試套件（111 題 pytest + 18 題 Node）執行耗時。',
        '1. 本地快篩響應時間小於 500ms。\n2. 雲端綜合診斷平均耗時於 3~8 秒內完成（總體上限 15 秒）。\n3. 全套自動化回歸測試於 20 秒內全數通過。'
    ]
]


def build_table_10_1_element(headers, rows):
    """Constructs a clean 3-column Word table XML element matching original styling."""
    xml_parts = [
        '<w:tbl xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">',
        '  <w:tblPr>',
        '    <w:tblStyle w:val="aff2"/>',
        '    <w:tblW w:w="9468" w:type="dxa"/>',
        '    <w:jc w:val="center"/>',
        '    <w:tblBorders>',
        '      <w:top w:val="single" w:sz="4" w:space="0" w:color="auto"/>',
        '      <w:left w:val="none" w:sz="0" w:space="0" w:color="auto"/>',
        '      <w:bottom w:val="single" w:sz="4" w:space="0" w:color="auto"/>',
        '      <w:right w:val="none" w:sz="0" w:space="0" w:color="auto"/>',
        '      <w:insideH w:val="single" w:sz="4" w:space="0" w:color="auto"/>',
        '      <w:insideV w:val="none" w:sz="0" w:space="0" w:color="auto"/>',
        '    </w:tblBorders>',
        '    <w:tblCellMar>',
        '      <w:top w:w="120" w:type="dxa"/>',
        '      <w:left w:w="160" w:type="dxa"/>',
        '      <w:bottom w:w="120" w:type="dxa"/>',
        '      <w:right w:w="160" w:type="dxa"/>',
        '    </w:tblCellMar>',
        '    <w:tblLook w:val="04A0" w:firstRow="1" w:lastRow="0" w:firstColumn="1" w:lastColumn="0" w:noHBand="0" w:noVBand="1"/>',
        '  </w:tblPr>',
        '  <w:tblGrid>'
    ]
    for w in COL_WIDTHS_10_1:
        xml_parts.append(f'    <w:gridCol w:w="{w}"/>')
    xml_parts.append('  </w:tblGrid>')

    # Header Row
    xml_parts.append('  <w:tr>')
    xml_parts.append('    <w:trPr><w:tblHeader/><w:cantSplit/><w:jc w:val="center"/></w:trPr>')
    for col_idx, (text, w) in enumerate(zip(headers, COL_WIDTHS_10_1)):
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
        for col_idx, (text, w) in enumerate(zip(row_data, COL_WIDTHS_10_1)):
            align = 'center' if col_idx == 0 else 'left'
            bold_xml = '<w:b/>' if col_idx == 0 else ''
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
            if bold_xml:
                xml_parts.append(f'            {bold_xml}')
            xml_parts.append('            <w:sz w:val="21"/>')
            xml_parts.append('            <w:szCs w:val="21"/>')
            xml_parts.append('            <w:lang w:eastAsia="zh-TW"/>')
            xml_parts.append('          </w:rPr>')

            # split lines with <w:br/>
            lines = text.split('\n')
            for l_idx, line in enumerate(lines):
                if l_idx > 0:
                    xml_parts.append('<w:br/>')
                xml_parts.append(f'<w:t>{escape(line)}</w:t>')

            xml_parts.append('        </w:r>')
            xml_parts.append('      </w:p>')
            xml_parts.append('    </w:tc>')
        xml_parts.append('  </w:tr>')

    xml_parts.append('</w:tbl>')
    return parse_xml(''.join(xml_parts))


def build_intro_paragraph():
    """Builds the introductory paragraph before Table 10-1-1."""
    text = '為確保本植物病蟲害辨識系統在演算法精準度、即時監控可靠性、前後端資料交換契約一致性及系統資安防護之穩定運作，本系統制定涵蓋單元測試、AI階層與三方仲裁測試、Webcam防抖共識測試、RAG向量檢索測試、介面契約測試、安全與權限控制測試、端到端整合測試及效能可靠度測試等八大層級之完整測試計畫，測試策略與驗收目標如表 10-1-1 所示。'
    xml = f"""<w:p xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:pPr>
    <w:pStyle w:val="af7"/>
    <w:ind w:left="280" w:right="280" w:firstLine="454"/>
    <w:rPr>
      <w:rFonts w:hint="eastAsia"/>
      <w:lang w:eastAsia="zh-TW"/>
    </w:rPr>
  </w:pPr>
  <w:r>
    <w:rPr>
      <w:rFonts w:ascii="微軟正黑體" w:hAnsi="微軟正黑體" w:eastAsia="微軟正黑體"/>
      <w:lang w:eastAsia="zh-TW"/>
    </w:rPr>
    <w:t>{escape(text)}</w:t>
  </w:r>
</w:p>"""
    return parse_xml(xml)


def update_section_10_1_in_doc(docx_path):
    print(f"\n=======================================================")
    print(f"Processing Section 10-1 in: {docx_path}")
    if not os.path.exists(docx_path):
        print("  File not found! Skipping.")
        return False

    doc = docx.Document(docx_path)
    body_el = doc._body._element

    # 1. Locate the caption paragraph for 表 10-1-1
    caption_p = None
    caption_idx = -1
    for i, el in enumerate(body_el):
        if el.tag.endswith('}p'):
            t_txt = ''.join([n.text or '' for n in el.iter(qn('w:t'))])
            has_tab = '\t' in t_txt or any(n.tag.endswith('}tab') for n in el.iter())
            if not has_tab and ('測試計畫表' in t_txt or '測試策略表' in t_txt):
                caption_p = el
                caption_idx = i
                break

    if caption_p is None:
        print("  Caption for 表 10-1-1 not found!")
        return False

    print(f"  Found caption paragraph at index {caption_idx}.")

    # 2. Check / insert introductory paragraph before caption
    prec_p = body_el[caption_idx - 1] if caption_idx > 0 else None
    prec_txt = ''.join([n.text or '' for n in prec_p.iter(qn('w:t'))]) if prec_p is not None else ''
    if '為確保本植物病蟲害辨識系統' in prec_txt or '本系統為確保在演算法精準度' in prec_txt:
        print("  Introductory paragraph already present.")
    else:
        print(f"  Preceding element text: '{prec_txt}'. Inserting introductory paragraph...")
        intro_el = build_intro_paragraph()
        body_el.insert(caption_idx, intro_el)
        caption_idx += 1  # adjusted since we inserted an element before it
        print("  Successfully inserted introductory paragraph.")

    # 3. Locate the table immediately following the caption
    target_table_el = None
    for next_idx in range(caption_idx + 1, min(len(body_el), caption_idx + 5)):
        if body_el[next_idx].tag.endswith('}tbl'):
            target_table_el = body_el[next_idx]
            break

    if target_table_el is not None:
        new_tbl_el = build_table_10_1_element(HEADERS_10_1, ROWS_10_1)
        tbl_idx = body_el.index(target_table_el)
        body_el.insert(tbl_idx, new_tbl_el)
        body_el.remove(target_table_el)
        print("  Successfully refreshed 表 10-1-1 table (8 rows, 9468 dxa).")
    else:
        print("  Warning: Table following caption not found!")

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
            update_section_10_1_in_doc(tf)
        except Exception as e:
            print(f"  Error on {tf}: {e}")
            import traceback
            traceback.print_exc()
