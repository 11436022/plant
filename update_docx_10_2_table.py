import copy
import os
import sys
from xml.sax.saxutils import escape
import docx
from docx.oxml import parse_xml
from docx.oxml.ns import qn

sys.stdout.reconfigure(encoding='utf-8')

HEADERS_10_2 = ['編號', '測試項目', '預期結果', '測試結果與查核證據']
COL_WIDTHS_10_2 = [1100, 2800, 2800, 2768]  # total = 9468 dxa

ROWS_10_2 = [
    [
        'TC-01',
        '正常帳號登入驗證：\n輸入已完成信箱驗證的帳號與正確密碼，點擊登入。',
        '系統成功簽發 JWT Access Token，前端跳轉至應用程式主畫面。',
        '通過 (Pass)\ntest_api_regressions.py 驗證 Token 簽發與授權標頭解析正常。'
    ],
    [
        'TC-02',
        '密碼錯誤與防帳號探測：\n輸入錯誤密碼或未註冊帳號嘗試登入。',
        '系統拒絕存取，統一口徑回傳「帳號或密碼錯誤」通用提示，不洩漏帳號是否存在。',
        '通過 (Pass)\ntest_auth.py 驗證密碼校驗邏輯，統一回傳 400 錯誤防範帳號枚舉。'
    ],
    [
        'TC-03',
        '新用戶註冊與郵件驗證：\n輸入有效電子信箱與密碼註冊，並完成一次性權杖信箱驗證。',
        '建立待驗證帳號並發送驗證信；未驗證前拒絕存取受保護端點，驗證後方可登入。',
        '通過 (Pass)\ntest_api_regressions.py 驗證 Pending 攔截，SHA-256 單次權杖比對無誤。'
    ],
    [
        'TC-04',
        '水平越權防護 (IDOR)：\n使用者 A 嘗試透過 API 確認、修改或刪除屬於使用者 B 的診斷記錄。',
        '系統自動攔截並回傳 403 Forbidden 或 404，嚴格禁止跨帳號非法存取。',
        '通過 (Pass)\ntest_api_regressions.py 驗證診斷紀錄擁有權檢查（Ownership Check），越權操作全數阻擋。'
    ],
    [
        'TC-05',
        '本地 ConvNeXt 快篩命中：\n上傳清晰且屬於本地 15 類白名單之常見病害影像（如番茄早疫病）。',
        '本地 PyTorch 卷積模型毫秒級完成邊緣快篩，高信心命中直接輸出診斷，無需調用雲端。',
        '通過 (Pass)\ntest_cascade_diagnosis.py（17 項）驗證權重映射正確，Tier-1 快篩響應時間 <500ms。'
    ],
    [
        'TC-06',
        '三方仲裁器衝突裁決：\n輸入爭議影像（如雙模型判斷不一、或木槿白化症生理現象 vs 病斑）。',
        '三方仲裁器啟動，依模型信心權重、地面真值與語意特徵進行仲裁，精準排除誤判。',
        '通過 (Pass)\ntest_tripartite_arbiter.py（6 項）驗證雙中同判定與白化症病斑衝突裁決完全符合預期。'
    ],
    [
        'TC-07',
        '域外作物 (OOD) 排除與反向救援：\n上傳非支援之域外作物（如草莓）或冷門植株特徵。',
        '仲裁器主動剔除高信心之錯誤標籤，啟動反向救援保護機制，不產生錯誤定論。',
        '通過 (Pass)\ntest_tripartite_arbiter.py 驗證 OOD 樣本排除邏輯，防止模型強行歸類。'
    ],
    [
        'TC-08',
        '防幻覺校驗 (Database Grounding)：\n大語言模型生成推論時產出非農業部核准之虛構病害名稱。',
        '防幻覺過濾器精準攔截，強制置換為農業專家資料庫核准之標準病害與官方防治指南。',
        '通過 (Pass)\ntest_ai_validation.py（7 項）驗證地面真值替換，成功杜絕大模型幻覺。'
    ],
    [
        'TC-09',
        '視訊壞幀前置過濾：\nWebcam 串流傳入過小、全黑或嚴重模糊缺乏細節之影像幀。',
        '影像檢查函式於推論前直接拒絕，回傳 400 錯誤，不調用模型以節約伺服器運算資源。',
        '通過 (Pass)\ntest_webcam.py 驗證各類壞幀與無細節影像即時攔截，且伺服器不留暫存檔。'
    ],
    [
        'TC-10',
        '連續 3 幀共識防抖：\nWebcam 即時監控中偶發 1~2 幀短暫雜訊或不同病斑判定。',
        '系統累積連續計數（Streak），未達連續 3 幀相同異常前不觸發警報；中途出現健康幀立即重置。',
        '通過 (Pass)\ntest_webcam.py 及 Node.js 18 項測試通過，確認共識計數器防誤報邏輯正確。'
    ],
    [
        'TC-11',
        '警報非同步隔離與持久化：\n達到警報觸發門檻時，模擬 SMTP 郵件伺服器連線超時或寄信失敗。',
        '郵件錯誤不影響警報核心事務，警報紀錄仍成功寫入資料庫，快照圖檔妥善保留於伺服器。',
        '通過 (Pass)\ntest_webcam_persistence_regressions.py 驗證事務解耦，email_sent=False 狀態正確留存。'
    ],
    [
        'TC-12',
        'RAG 向量知識庫 Manifest 雜湊檢核：\n後端啟動時檢驗 FAISS 索引檔、知識文本與清單雜湊（SHA-256）。',
        '雜湊相符時成功載入並支援語意檢索；若檔案遭竄改或損毀，主動拒絕載入並安全降級。',
        '通過 (Pass)\ntest_backend_manifest_regressions.py（13 項）驗證真實 FAISS 檢索與雜湊損毀防護。'
    ],
    [
        'TC-13',
        'Android 行動端 API 契約測試：\nAndroid 端透過 Retrofit DTO 反序列化後端回傳之診斷 JSON 結構。',
        '完整解析信心值、來源與文獻 URL；舊版欄位缺失時安全降級不閃退；信心值明確附帶免責聲明。',
        '通過 (Pass)\nDiagnosisContractTest.kt（11 項契約測試）通過，確保前後端資料契約零落差。'
    ],
    [
        'TC-14',
        '違規非圖片檔案上傳阻擋：\n使用者嘗試上傳 .txt、.pdf 或偽造副檔名之無效檔案。',
        '系統進行 Magic Bytes 與 MIME 型態雙重檢驗，直接拒絕上傳並提示「檔案格式不支援」。',
        '通過 (Pass)\ntest_api_regressions.py 驗證各類偽造 MIME 與非圖檔均回傳 400 客戶端錯誤。'
    ],
    [
        'TC-15',
        '診斷暫存入庫與植物日誌 CRUD：\n完成 AI 診斷後於有效時限內確認儲存，檢視歷史日誌並編輯備忘筆記。',
        '診斷快照寫入植物日誌；歷史依時間降冪排序；使用者筆記與原始 AI 診斷欄位各自獨立保存。',
        '通過 (Pass)\ntest_api_regressions.py 驗證重複確認防護、TTL 時限作廢與使用者自訂糾錯隔離。'
    ],
    [
        'TC-16',
        '端到端全流程與效能驗收：\n執行註冊 → 驗證 → 登入 → 上傳 → AI階層推論 → RAG檢索 → 歷史查看完整流程。',
        '各階段資料流交換完整；本地快篩延遲 <500ms，雲端綜合推論於 3~8 秒內完成（符合 15 秒目標）。',
        '通過 (Pass)\n端到端流程通過；後端 111 項 pytest 回歸套件於 17.84 秒內全數通過。'
    ]
]


def build_table_10_2_element(headers, rows):
    """Constructs a clean 4-column Word table XML element matching original styling."""
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
    for w in COL_WIDTHS_10_2:
        xml_parts.append(f'    <w:gridCol w:w="{w}"/>')
    xml_parts.append('  </w:tblGrid>')

    # Header Row
    xml_parts.append('  <w:tr>')
    xml_parts.append('    <w:trPr><w:tblHeader/><w:cantSplit/><w:jc w:val="center"/></w:trPr>')
    for col_idx, (text, w) in enumerate(zip(headers, COL_WIDTHS_10_2)):
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
        for col_idx, (text, w) in enumerate(zip(row_data, COL_WIDTHS_10_2)):
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


def build_intro_paragraph_10_2():
    """Builds the introductory paragraph before Table 10-2-1."""
    text = '本系統依據測試計畫針對使用者認證、AI 多層級診斷與仲裁、Webcam 即時監控防抖、RAG 向量知識庫、Android 行動端契約及系統端到端效能進行完整測試驗證，共設計 16 項具代表性之核心測試個案，各項測試之操作情境、預期結果與實際查核證據如表 10-2-1 所示。'
    xml = f"""<w:p xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:pPr>
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


def build_summary_note_10_2():
    """Builds the testing scope and limits summary note following Table 10-2-1."""
    text = '共同測試範圍與限制：後端自動化回歸套件（111 passed，耗時 17.84 秒）已全數執行通過，涵蓋真實 SQLite 與 FAISS 向量運作、來源清單雜湊比對、跨作物校驗及 Alembic 資料庫版本遷移；前端視訊串流防抖邏輯套件（18 passed）與 Android 行動端資料契約單元測試（11 passed）亦全數驗證通過。各項測試均留存對應之自動化測試程式與執行日誌作為查核證據。'
    xml = f"""<w:p xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:pPr>
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


def update_section_10_2_in_doc(docx_path):
    print(f"\n=======================================================")
    print(f"Processing Section 10-2 in: {docx_path}")
    if not os.path.exists(docx_path):
        print("  File not found! Skipping.")
        return False

    doc = docx.Document(docx_path)
    body_el = doc._body._element

    # 1. Locate the caption paragraph for 表 10-2-1
    caption_p = None
    caption_idx = -1
    for i, el in enumerate(body_el):
        if el.tag.endswith('}p'):
            t_txt = ''.join([n.text or '' for n in el.iter(qn('w:t'))])
            has_tab = '\t' in t_txt or any(n.tag.endswith('}tab') for n in el.iter())
            if not has_tab and '表' in t_txt and ('10-2' in t_txt or '測試個案' in t_txt or '測試案例' in t_txt):
                caption_p = el
                caption_idx = i
                break

    if caption_p is None:
        print("  Caption for 表 10-2-1 not found!")
        return False

    print(f"  Found caption paragraph at index {caption_idx}: '{''.join([n.text or '' for n in caption_p.iter(qn('w:t'))])}'")

    # 2. Check / insert introductory paragraph before caption
    prec_p = body_el[caption_idx - 1] if caption_idx > 0 else None
    prec_txt = ''.join([n.text or '' for n in prec_p.iter(qn('w:t'))]) if prec_p is not None else ''
    if '本系統依據測試計畫' in prec_txt:
        print("  Introductory paragraph already present.")
    else:
        print(f"  Preceding element text: '{prec_txt}'. Inserting introductory paragraph...")
        intro_el = build_intro_paragraph_10_2()
        body_el.insert(caption_idx, intro_el)
        caption_idx += 1  # adjusted since we inserted an element before it
        print("  Successfully inserted introductory paragraph.")

    # 3. Locate the table immediately following the caption
    target_table_el = None
    table_idx = -1
    for next_idx in range(caption_idx + 1, min(len(body_el), caption_idx + 5)):
        if body_el[next_idx].tag.endswith('}tbl'):
            target_table_el = body_el[next_idx]
            table_idx = next_idx
            break

    if target_table_el is not None:
        new_tbl_el = build_table_10_2_element(HEADERS_10_2, ROWS_10_2)
        tbl_pos = body_el.index(target_table_el)
        body_el.insert(tbl_pos, new_tbl_el)
        body_el.remove(target_table_el)
        print(f"  Successfully refreshed 表 10-2-1 table ({len(ROWS_10_2)} rows, 9468 dxa).")

        # 4. Check / update summary note after table
        post_idx = tbl_pos + 1
        post_p = body_el[post_idx] if post_idx < len(body_el) and body_el[post_idx].tag.endswith('}p') else None
        post_txt = ''.join([n.text or '' for n in post_p.iter(qn('w:t'))]) if post_p is not None else ''
        if '共同測試範圍與限制' in post_txt:
            print("  Updating existing summary note after table...")
            # replace text of existing summary note
            t_nodes = list(post_p.iter(qn('w:t')))
            if t_nodes:
                new_sum = '共同測試範圍與限制：後端自動化回歸套件（111 passed，耗時 17.84 秒）已全數執行通過，涵蓋真實 SQLite 與 FAISS 向量運作、來源清單雜湊比對、跨作物校驗及 Alembic 資料庫版本遷移；前端視訊串流防抖邏輯套件（18 passed）與 Android 行動端資料契約單元測試（11 passed）亦全數驗證通過。各項測試均留存對應之自動化測試程式與執行日誌作為查核證據。'
                t_nodes[0].text = new_sum
                for tn in t_nodes[1:]:
                    tn.text = ''
            print("  Updated summary note.")
        else:
            print("  Inserting summary note after table...")
            summary_el = build_summary_note_10_2()
            body_el.insert(post_idx, summary_el)
            print("  Successfully inserted summary note.")
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
            update_section_10_2_in_doc(tf)
        except Exception as e:
            print(f"  Error on {tf}: {e}")
            import traceback
            traceback.print_exc()
