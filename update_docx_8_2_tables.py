import copy
import os
import shutil
from xml.sax.saxutils import escape
import docx
from docx.oxml import parse_xml
from docx.oxml.ns import qn

HEADERS = ['欄位名稱', '欄位中文名稱', '資料型態', '資料長度', '索引']
COL_WIDTHS = [2317, 2552, 1865, 1570, 1148]  # dxa, total = 9452 dxa

TABLE_DEFS = {
    '8-2-1': {
        'title': '表 8-2-1 資料表-crop',
        'key': 'crop',
        'rows': [
            ['crop_id', '作物ID', 'int', '-', 'V'],
            ['crop_name', '作物名稱', 'varchar', '100', ''],
            ['crop_name_en', '作物英文名稱', 'varchar', '100', '']
        ]
    },
    '8-2-2': {
        'title': '表 8-2-2 資料表-disease',
        'key': 'disease',
        'rows': [
            ['disease_id', '病害ID', 'int', '-', 'V'],
            ['crop_id', '作物ID', 'int', '-', 'V'],
            ['disease_name', '病害名稱', 'varchar', '100', ''],
            ['description', '病徵病理描述', 'text', '-', ''],
            ['treatment', '防治建議措施', 'text', '-', ''],
            ['source_name', '資料來源', 'varchar', '100', ''],
            ['source_url', '圖庫來源網址', 'varchar', '2048', ''],
            ['source_record_id', '圖庫來源編號', 'varchar', '128', '']
        ]
    },
    '8-2-3': {
        'title': '表 8-2-3 資料表-pests',
        'key': 'pests',
        'rows': [
            ['pest_id', '蟲害ID', 'int', '-', 'V'],
            ['crop_id', '作物ID', 'int', '-', 'V'],
            ['pest_name', '蟲害名稱', 'varchar', '100', ''],
            ['description', '蟲害危害描述', 'text', '-', ''],
            ['treatment', '防治建議措施', 'text', '-', ''],
            ['source_name', '資料來源', 'varchar', '100', ''],
            ['source_url', '圖庫來源網址', 'varchar', '2048', ''],
            ['source_record_id', '圖庫來源編號', 'varchar', '128', '']
        ]
    },
    '8-2-4': {
        'title': '表 8-2-4 資料表-plant_diary',
        'key': 'plant_diary',
        'rows': [
            ['id', '日誌ID', 'int', '-', 'V'],
            ['user_id', '使用者ID', 'int', '-', 'V'],
            ['crop_id', '作物ID', 'int', '-', 'V'],
            ['status_name', '診斷病蟲害名稱', 'varchar', '100', ''],
            ['image_url', '診斷影像路徑', 'varchar', '2048', ''],
            ['disease_id', '病害ID', 'int', '-', 'V'],
            ['pest_id', '蟲害ID', 'int', '-', 'V'],
            ['confidence', 'AI信心度', 'float', '-', ''],
            ['category', '類別', 'varchar', '20', ''],
            ['requires_review', '是否需人工覆核', 'tinyint', '1', ''],
            ['grounding_source', '診斷佐證技術來源', 'varchar', '64', ''],
            ['reference_source', '參考資料來源', 'varchar', '100', ''],
            ['reference_url', '參考資料來源網址', 'varchar', '2048', ''],
            ['reference_record_id', '圖庫來源編號', 'varchar', '128', ''],
            ['suggestion', 'AI診斷建議', 'text', '-', ''],
            ['treatment', '處置措施', 'text', '-', ''],
            ['user_note', '使用者個人備註記錄', 'text', '-', ''],
            ['user_corrected_status', '使用者校正狀態', 'varchar', '100', ''],
            ['created_at', '診斷建立時間', 'datetime', '-', '']
        ]
    },
    '8-2-5': {
        'title': '表 8-2-5 資料表-user',
        'key': 'user',
        'rows': [
            ['user_id', '使用者ID', 'int', '-', 'V'],
            ['username', '使用者帳號', 'varchar', '50', 'V'],
            ['password_hash', '密碼雜湊值 (Bcrypt)', 'varchar', '255', ''],
            ['email', '電子信箱', 'varchar', '100', 'V'],
            ['full_name', '使用者真實姓名', 'varchar', '50', ''],
            ['role', '權限角色', 'varchar', '20', ''],
            ['is_email_verified', '電子信箱是否已驗證', 'tinyint', '1', ''],
            ['email_verified_at', '信箱驗證通過時間', 'datetime', '-', ''],
            ['created_at', '帳號建立時間', 'datetime', '-', '']
        ]
    },
    '8-2-6': {
        'title': '表 8-2-6 資料表-user_one_time_tokens',
        'key': 'user_one_time_tokens',
        'rows': [
            ['id', '權杖ID', 'bigint', '-', 'V'],
            ['user_id', '使用者ID', 'int', '-', 'V'],
            ['purpose', '權杖用途', 'varchar', '32', 'V'],
            ['token_hash', '權杖雜湊值 (SHA-256)', 'varchar', '64', 'V'],
            ['expires_at', '權杖到期時間', 'datetime', '-', ''],
            ['used_at', '權杖使用完成時間', 'datetime', '-', ''],
            ['created_at', '權杖建立時間', 'datetime', '-', '']
        ]
    },
    '8-2-7': {
        'title': '表 8-2-7 資料表-webcam_alert',
        'key': 'webcam_alert',
        'rows': [
            ['id', '警報ID', 'bigint', '-', 'V'],
            ['user_id', '使用者ID', 'int', '-', 'V'],
            ['crop_id', '作物ID', 'int', '-', 'V'],
            ['category', '類別', 'varchar', '20', ''],
            ['status_name', '警報病害或蟲害名稱', 'varchar', '100', ''],
            ['confidence', '辨識信心度', 'float', '-', ''],
            ['requires_review', '是否需人工覆核', 'tinyint', '1', ''],
            ['grounding_source', '診斷佐證技術來源', 'varchar', '64', ''],
            ['reference_source', '參考資料來源', 'varchar', '100', ''],
            ['reference_url', '參考資料來源網址', 'varchar', '2048', ''],
            ['reference_record_id', '圖庫來源編號', 'varchar', '128', ''],
            ['session_id', '監控串流連線ID', 'varchar', '64', 'V'],
            ['region_id', '監控區域編號', 'varchar', '64', ''],
            ['consecutive_matches', '連續辨識命中影格數', 'int', '-', ''],
            ['image_url', '警報快照影像路徑', 'varchar', '2048', ''],
            ['email_sent', '是否已發送通知信', 'tinyint', '1', ''],
            ['acknowledged_at', '使用者確認已讀時間', 'datetime', '-', ''],
            ['created_at', '警報觸發建立時間', 'datetime', '-', '']
        ]
    },
    '8-2-8': {
        'title': '表 8-2-8 資料表-diagnosis_feedback',
        'key': 'diagnosis_feedback',
        'rows': [
            ['id', '回饋ID', 'int', '-', 'V'],
            ['prediction_id', '關聯診斷序號', 'varchar', '64', 'V'],
            ['user_id', '使用者ID (可匿名)', 'int', '-', 'V'],
            ['image_url', '回饋圖片路徑', 'varchar', '255', ''],
            ['original_plant_name', 'AI判定作物名稱', 'varchar', '100', ''],
            ['original_disease_name', 'AI判定病蟲害名稱', 'varchar', '100', ''],
            ['is_plant_error', '作物判定是否錯誤', 'tinyint', '1', ''],
            ['is_disease_error', '病蟲害判定是否錯誤', 'tinyint', '1', ''],
            ['corrected_plant_name', '使用者更正作物名稱', 'varchar', '100', ''],
            ['corrected_disease_name', '使用者更正病蟲害名稱', 'varchar', '100', ''],
            ['created_at', '回饋建立時間', 'datetime', '-', '']
        ]
    }
}


def build_table_element(headers, rows):
    """Constructs a clean, 5-column Word table XML element."""
    xml_parts = [
        '<w:tbl xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">',
        '  <w:tblPr>',
        '    <w:tblStyle w:val="aff2"/>',
        '    <w:tblW w:w="9452" w:type="dxa"/>',
        '    <w:jc w:val="center"/>',
        '    <w:tblLook w:val="04A0" w:firstRow="1" w:lastRow="0" w:firstColumn="1" w:lastColumn="0" w:noHBand="0" w:noVBand="1"/>',
        '  </w:tblPr>',
        '  <w:tblGrid>'
    ]
    for w in COL_WIDTHS:
        xml_parts.append(f'    <w:gridCol w:w="{w}"/>')
    xml_parts.append('  </w:tblGrid>')

    # Header Row
    xml_parts.append('  <w:tr>')
    xml_parts.append('    <w:trPr><w:cantSplit/><w:jc w:val="center"/></w:trPr>')
    for col_idx, (text, w) in enumerate(zip(headers, COL_WIDTHS)):
        xml_parts.append('    <w:tc>')
        xml_parts.append('      <w:tcPr>')
        xml_parts.append(f'        <w:tcW w:w="{w}" w:type="dxa"/>')
        xml_parts.append('        <w:shd w:val="clear" w:color="auto" w:fill="DDEAD7"/>')
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
        for col_idx, (text, w) in enumerate(zip(row_data, COL_WIDTHS)):
            align = 'center' if col_idx in (3, 4) else 'left'
            xml_parts.append('    <w:tc>')
            xml_parts.append('      <w:tcPr>')
            xml_parts.append(f'        <w:tcW w:w="{w}" w:type="dxa"/>')
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


def build_caption_element(title_text):
    """Builds a standard Caption paragraph element."""
    xml = f"""<w:p xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
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
    <w:t>{escape(title_text)}</w:t>
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


def identify_caption_key(para_el):
    """Identifies which table (8-2-1 to 8-2-8) this caption paragraph belongs to."""
    if any(n.tag.endswith('}tab') for n in para_el.iter()):
        return None
    txt = ''.join([n.text or '' for n in para_el.iter(qn('w:t'))]).strip()
    if not txt.startswith('表') or len(txt) > 60:
        return None
    if '資料表' not in txt and '8-2' not in txt:
        return None
    if 'crop' in txt: return '8-2-1'
    if 'disease' in txt: return '8-2-2'
    if 'pests' in txt or 'pest' in txt: return '8-2-3'
    if 'plant_diary' in txt: return '8-2-4'
    if 'user_one_time_tokens' in txt: return '8-2-6'
    if 'webcam_alert' in txt: return '8-2-7'
    if 'diagnosis_feedback' in txt: return '8-2-8'
    if 'user' in txt: return '8-2-5'
    return None


def update_document(docx_path):
    print(f"\n=======================================================")
    print(f"Processing: {docx_path}")
    if not os.path.exists(docx_path):
        print("  File not found! Skipping.")
        return False

    doc = docx.Document(docx_path)
    body_el = doc._body._element

    # 1. Update Table of Tables (表目錄)
    p78_entry = None
    p826_entry = None
    has_8_2_7_toc = False
    has_8_2_8_toc = False

    for el in body_el:
        if el.tag.endswith('}p'):
            t_txt = ''.join([n.text or '' for n in el.iter(qn('w:t'))])
            has_tab = '\t' in t_txt or any(n.tag.endswith('}tab') for n in el.iter())
            if has_tab:
                if '8-2-8' in t_txt or 'diagnosis_feedback' in t_txt:
                    has_8_2_8_toc = True
                if '8-2-7' in t_txt or 'webcam_alert' in t_txt:
                    has_8_2_7_toc = True
                    p78_entry = el
                if '8-2-6' in t_txt or 'user_one_time_tokens' in t_txt:
                    p826_entry = el

    # Fix or insert into TOC
    if p78_entry is not None:
        # Check if page number is '4' and fix it to '40'
        t_nodes = list(p78_entry.iter(qn('w:t')))
        for tn in t_nodes:
            if tn.text == '4':
                print("  Fixing 表 8-2-7 TOC page number from '4' to '40'")
                tn.text = '40'

        # Insert 8-2-8 TOC entry if missing
        if not has_8_2_8_toc:
            print("  Adding 表 8-2-8 into Table of Tables (表目錄)")
            clone_828 = copy.deepcopy(p78_entry)
            for tn in clone_828.iter(qn('w:t')):
                if tn.text and '8-2-7' in tn.text:
                    tn.text = tn.text.replace('8-2-7', '8-2-8')
                elif tn.text and 'webcam_alert' in tn.text:
                    tn.text = tn.text.replace('webcam_alert', 'diagnosis_feedback')
                elif tn.text in ('4', '40'):
                    tn.text = '41'
            p_parent = p78_entry.getparent()
            p_parent.insert(p_parent.index(p78_entry) + 1, clone_828)
    elif p826_entry is not None:
        # Document only had up to 8-2-6 in TOC
        print("  Adding 表 8-2-7 and 表 8-2-8 into Table of Tables (表目錄)")
        clone_827 = copy.deepcopy(p826_entry)
        for tn in clone_827.iter(qn('w:t')):
            if tn.text and '8-2-6' in tn.text:
                tn.text = tn.text.replace('8-2-6', '8-2-7')
            elif tn.text and 'user_one_time_tokens' in tn.text:
                tn.text = tn.text.replace('user_one_time_tokens', 'webcam_alert')
        clone_828 = copy.deepcopy(p826_entry)
        for tn in clone_828.iter(qn('w:t')):
            if tn.text and '8-2-6' in tn.text:
                tn.text = tn.text.replace('8-2-6', '8-2-8')
            elif tn.text and 'user_one_time_tokens' in tn.text:
                tn.text = tn.text.replace('user_one_time_tokens', 'diagnosis_feedback')
            elif tn.text == '30':
                tn.text = '31'

        p_parent = p826_entry.getparent()
        idx = p_parent.index(p826_entry)
        p_parent.insert(idx + 1, clone_827)
        p_parent.insert(idx + 2, clone_828)

    # 2. Update Body Tables (8-2-1 to 8-2-8)
    caption_elements = {}
    table_elements = {}

    for i, el in enumerate(body_el):
        if el.tag.endswith('}p'):
            k = identify_caption_key(el)
            if k:
                caption_elements[k] = el
                # Find immediately following table
                for j in range(i + 1, min(i + 25, len(body_el))):
                    sub_el = body_el[j]
                    if sub_el.tag.endswith('}tbl'):
                        table_elements[k] = sub_el
                        break
                    elif sub_el.tag.endswith('}p'):
                        sub_k = identify_caption_key(sub_el)
                        if sub_k:
                            break

    print(f"  Found captions: {sorted(list(caption_elements.keys()))}")
    print(f"  Found tables: {sorted(list(table_elements.keys()))}")

    # Replace existing tables 8-2-1 to 8-2-8
    for key in ['8-2-1', '8-2-2', '8-2-3', '8-2-4', '8-2-5', '8-2-6', '8-2-7', '8-2-8']:
        if key in table_elements:
            old_tbl = table_elements[key]
            new_tbl = build_table_element(HEADERS, TABLE_DEFS[key]['rows'])
            old_tbl.getparent().replace(old_tbl, new_tbl)
            table_elements[key] = new_tbl  # Point to active new element
            print(f"  Replaced Table {key} with clean 5-column table ({len(TABLE_DEFS[key]['rows'])} rows).")

    # Clean up empty paragraphs between Table 8-2-7 and 表 8-2-8 caption if needed
    if '8-2-7' in table_elements and '8-2-8' in caption_elements:
        p828_el = caption_elements['8-2-8']
        idx_p828 = body_el.index(p828_el)
        empty_paras = []
        for k in range(idx_p828 - 1, 0, -1):
            cur_el = body_el[k]
            if cur_el.tag.endswith('}p'):
                cur_txt = ''.join([n.text or '' for n in cur_el.iter(qn('w:t'))]).strip()
                if not cur_txt:
                    empty_paras.append(cur_el)
                else:
                    break
            else:
                break
        if len(empty_paras) > 1:
            print(f"  Cleaning up {len(empty_paras) - 1} excess empty paragraphs before 表 8-2-8...")
            for ep in empty_paras[1:]:
                ep.getparent().remove(ep)

    # If 8-2-8 does NOT exist in body, insert caption and table after Table 8-2-7
    if '8-2-8' not in caption_elements:
        if '8-2-7' in table_elements:
            target_el = table_elements['8-2-7']
            parent = target_el.getparent()
            idx = parent.index(target_el)
            print("  Inserting 表 8-2-8 caption and table after Table 8-2-7...")
            parent.insert(idx + 1, build_empty_p())
            c828 = build_caption_element(TABLE_DEFS['8-2-8']['title'])
            parent.insert(idx + 2, c828)
            t828 = build_table_element(HEADERS, TABLE_DEFS['8-2-8']['rows'])
            parent.insert(idx + 3, t828)
            caption_elements['8-2-8'] = c828
            table_elements['8-2-8'] = t828
            print("  Successfully inserted 表 8-2-8 caption and table.")
        elif '8-2-6' in table_elements:
            target_el = table_elements['8-2-6']
            parent = target_el.getparent()
            idx = parent.index(target_el)
            print("  Inserting 表 8-2-7 and 表 8-2-8 after Table 8-2-6...")
            parent.insert(idx + 1, build_empty_p())
            c827 = build_caption_element(TABLE_DEFS['8-2-7']['title'])
            parent.insert(idx + 2, c827)
            t827 = build_table_element(HEADERS, TABLE_DEFS['8-2-7']['rows'])
            parent.insert(idx + 3, t827)
            parent.insert(idx + 4, build_empty_p())
            c828 = build_caption_element(TABLE_DEFS['8-2-8']['title'])
            parent.insert(idx + 5, c828)
            t828 = build_table_element(HEADERS, TABLE_DEFS['8-2-8']['rows'])
            parent.insert(idx + 6, t828)
            print("  Successfully inserted 表 8-2-7 and 表 8-2-8.")

    doc.save(docx_path)
    print(f"  Saved updated document: {docx_path}")
    return True


if __name__ == '__main__':
    target_files = [
        r'd:\plant_backend\documents\系統手冊_1.docx',
        r'd:\plant_backend\documents\系統手冊.docx',
        r'd:\plant_backend\documents\系統手冊前八章.docx',
        r'C:\Users\User\Downloads\系統手冊 (1).docx',
        r'C:\Users\User\Downloads\系統手冊.docx',
        r'C:\Users\User\OneDrive\文件\系統手冊.docx',
    ]
    for tf in target_files:
        try:
            update_document(tf)
        except Exception as e:
            print(f"  Error processing {tf}: {e}")
            import traceback
            traceback.print_exc()
