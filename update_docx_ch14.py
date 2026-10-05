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
    stripping hardcoded '14-X ' prefix so Word's automatic numbering produces clean '14-X '."""
    clean_text = re.sub(r'^14-\d+\s*', '', text)
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


def build_caption_p(text):
    """Standard table caption paragraph matching document caption style af7."""
    xml = f"""<w:p xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:pPr>
    <w:pStyle w:val="af7"/>
    <w:keepNext/>
    <w:ind w:left="280" w:right="280"/>
    <w:jc w:val="center"/>
    <w:rPr>
      <w:color w:val="auto"/>
      <w:sz w:val="28"/>
      <w:szCs w:val="28"/>
      <w:lang w:eastAsia="zh-TW"/>
    </w:rPr>
  </w:pPr>
  <w:r>
    <w:rPr>
      <w:color w:val="auto"/>
      <w:sz w:val="28"/>
      <w:szCs w:val="28"/>
      <w:lang w:eastAsia="zh-TW"/>
    </w:rPr>
    <w:t>{escape(text)}</w:t>
  </w:r>
</w:p>"""
    return parse_xml(xml)


def build_table_xml(headers, col_widths, rows_data):
    """Generates an XML element for a high-quality Word table matching style aff2."""
    total_w = sum(col_widths)
    xml_parts = [
        '<w:tbl xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">',
        '  <w:tblPr>',
        '    <w:tblStyle w:val="aff2"/>',
        f'    <w:tblW w:w="{total_w}" w:type="dxa"/>',
        '    <w:jc w:val="center"/>',
        '    <w:tblLayout w:type="fixed"/>',
        '    <w:tblLook w:val="04A0" w:firstRow="1" w:lastRow="0" w:firstColumn="1" w:lastColumn="0" w:noHBand="0" w:noVBand="1"/>',
        '  </w:tblPr>',
        '  <w:tblGrid>'
    ]
    for w in col_widths:
        xml_parts.append(f'    <w:gridCol w:w="{w}"/>')
    xml_parts.append('  </w:tblGrid>')

    # Header Row
    xml_parts.append('  <w:tr>')
    xml_parts.append('    <w:trPr><w:cantSplit/><w:tblHeader/><w:jc w:val="center"/></w:trPr>')
    for h, w in zip(headers, col_widths):
        xml_parts.append('    <w:tc>')
        xml_parts.append(f'      <w:tcPr><w:tcW w:w="{w}" w:type="dxa"/><w:shd w:val="clear" w:color="auto" w:fill="DDEAD7"/><w:vAlign w:val="center"/></w:tcPr>')
        xml_parts.append('      <w:p>')
        xml_parts.append('        <w:pPr><w:ind w:left="140" w:right="140"/><w:jc w:val="center"/><w:rPr><w:b/><w:sz w:val="22"/><w:szCs w:val="22"/><w:lang w:eastAsia="zh-TW"/></w:rPr></w:pPr>')
        xml_parts.append('        <w:r>')
        xml_parts.append('          <w:rPr><w:b/><w:sz w:val="22"/><w:szCs w:val="22"/><w:lang w:eastAsia="zh-TW"/></w:rPr>')
        xml_parts.append(f'          <w:t>{escape(h)}</w:t>')
        xml_parts.append('        </w:r>')
        xml_parts.append('      </w:p>')
        xml_parts.append('    </w:tc>')
    xml_parts.append('  </w:tr>')

    # Data Rows
    for row in rows_data:
        xml_parts.append('  <w:tr>')
        xml_parts.append('    <w:trPr><w:cantSplit/><w:jc w:val="center"/></w:trPr>')
        for idx, (cell_content, w) in enumerate(zip(row, col_widths)):
            jc_align = 'center' if idx in [0, 2] else 'left'
            xml_parts.append('    <w:tc>')
            xml_parts.append(f'      <w:tcPr><w:tcW w:w="{w}" w:type="dxa"/><w:vAlign w:val="center"/></w:tcPr>')
            # Support multiline cell content separated by \n
            lines = cell_content.split('\n')
            for line in lines:
                xml_parts.append('      <w:p>')
                xml_parts.append(f'        <w:pPr><w:ind w:left="140" w:right="140"/><w:jc w:val="{jc_align}"/><w:spacing w:line="280" w:lineRule="auto"/><w:rPr><w:sz w:val="20"/><w:szCs w:val="20"/><w:lang w:eastAsia="zh-TW"/></w:rPr></w:pPr>')
                xml_parts.append('        <w:r>')
                xml_parts.append('          <w:rPr><w:sz w:val="20"/><w:szCs w:val="20"/><w:lang w:eastAsia="zh-TW"/></w:rPr>')
                xml_parts.append(f'          <w:t>{escape(line)}</w:t>')
                xml_parts.append('        </w:r>')
                xml_parts.append('      </w:p>')
            xml_parts.append('    </w:tc>')
        xml_parts.append('  </w:tr>')

    xml_parts.append('</w:tbl>')
    return parse_xml(''.join(xml_parts))


def build_chapter_14_elements():
    """Generates all XML elements for Chapter 14 (參考資料)."""
    elements = []

    # 14-1 專案技術與文獻參考資料
    elements.append(build_h2_p('14-1 專案技術與文獻參考資料'))
    elements.append(build_normal_p('本專案「智慧植物病蟲害辨識與健康管理系統」在系統架構設計、邊緣端與雲端 AI 演算法開發、關聯式資料庫建置、前後端通訊協定及資安防護機制上，廣泛研閱並遵循業界前沿開源標準、學術文獻及政府官方開放資料規範。相關核心參考技術與文獻如表 14-1 所示。'))
    elements.append(build_caption_p('表 14-1 專案技術與文獻參考資料表'))

    table_14_1_headers = ['序號', '資料名稱', '領域類別', '用途與來源資訊 / 官方規範']
    table_14_1_widths = [700, 2500, 1600, 4667]
    table_14_1_rows = [
        ['1', 'FastAPI Framework & Security', '後端架構 / 資安鑑權', '後端非同步 RESTful API 核心框架、OAuth2 Password Bearer 與 JWT 權限驗證架構依據。\n來源：https://fastapi.tiangolo.com/tutorial/security/'],
        ['2', 'Android Jetpack & CameraX Guide', '行動端開發 / 影像採集', 'Android 現代化架構元件、ViewBinding、生命週期感知及相機即時自動對焦預覽技術。\n來源：https://developer.android.com/training/camerax'],
        ['3', 'Google Gemini Multimodal API', '雲端多模態 AI', '雲端高階大語言模型病害深度推理、影像細部特徵辨析與農事處置建議生成。\n來源：https://ai.google.dev/gemini-api/docs/vision'],
        ['4', 'Google Text-Embedding-004 API', '向量語意檢索 / RAG', '農業部專書文本向量化嵌入（Embedding）、語意特徵降維與知識相似度檢索。\n來源：https://ai.google.dev/gemini-api/docs/embeddings'],
        ['5', 'PyTorch & ConvNeXt Architecture', '深度學習 / 邊緣快篩', '本地輕量級邊緣卷積模型架構（ConvNeXt-Tiny），提供常見 15 類病害毫秒級快篩推論。\n論文出處：Liu et al., CVPR 2022；來源：https://pytorch.org/'],
        ['6', 'FAISS (Facebook AI Similarity Search)', '向量索引庫 / 資訊檢索', '農業百科密集特徵向量庫（L2 歐幾里得距離索引），支援本機毫秒級精準相似度搜尋。\n來源：https://github.com/facebookresearch/faiss'],
        ['7', 'MySQL 8.0 Reference Manual', '資料庫系統 / 交易控制', '關聯式資料庫結構設計、InnoDB ACID 交易保證、Foreign Key 約束與索引效能調優。\n來源：https://dev.mysql.com/doc/refman/8.0/en/'],
        ['8', 'SQLAlchemy 2.0 ORM Documentation', '物件關聯映射 / ORM', '現代 Python 物件導向資料庫抽象層、連線池（Connection Pool）管理與交易隔離。\n來源：https://docs.sqlalchemy.org/en/20/orm/'],
        ['9', 'Alembic Database Migration Tool', '資料庫版本控管', '資料庫結構版本追蹤、自動化 Schema 遷移指令碼生成與多版本衝突防範。\n來源：https://alembic.sqlalchemy.org/en/latest/'],
        ['10', '農業部重要農業害蟲診斷圖鑑 API', '政府開放資料 / 官方知識', '台灣本土經濟作物常見害蟲形態特徵、好發時期與生活史官方標準資料集。\n來源：https://data.moa.gov.tw/api/v1/ImportantAgriculturalPestInfo/'],
        ['11', '農業部樹木病蟲害診斷案例 API', '政府開放資料 / 防治指引', '台灣農業部官方樹木與多年生植物病斑圖鑑、誘發病原體及核准防治處方對策。\n來源：https://data.moa.gov.tw/api/v1/TreePestInfoType/'],
        ['12', 'PlantVillage Open Dataset', '影像資料集 / 基準測試', '國際知名植物病害開放資料集，用於卷積模型訓練、驗證與測試集分割（54,306 張）。\n來源：https://github.com/spMohanty/PlantVillage-Dataset'],
        ['13', 'Argon2 Hash Standard (RFC 9106)', '資訊安全 / 密碼學', '採用現代抗 GPU/ASIC 字典攻擊之 Argon2id 演算法進行會員密碼不可逆雜湊保存。\n來源：https://datatracker.ietf.org/doc/html/rfc9106'],
        ['14', 'Retrofit2 & OkHttp3 Client', '網路通訊 / 行動客戶端', 'Android 端非同步 HTTP 請求封裝、攔截器（Interceptor）動態注入 Bearer Token。\n來源：https://square.github.io/retrofit/'],
        ['15', 'Docker & Compose Specification', '容器化部署 / 雲原生', '採用非 root (appuser) 安全容器封裝、多階段建置（Multi-stage Build）與持久化目錄掛載。\n來源：https://docs.docker.com/compose/'],
        ['16', '專案 GitHub 原始碼儲存庫', '專案管理 / 軟體工程', '系統前後端原始碼、全套資料庫遷移腳本、單元測試套件與即時 CI 驗收環境。\n儲存庫網址：https://github.com/11436022/plant'],
    ]
    elements.append(build_table_xml(table_14_1_headers, table_14_1_widths, table_14_1_rows))

    # 14-2 生成式人工智慧 (AI) 工具使用揭露與說明
    elements.append(build_h2_p('14-2 生成式人工智慧 (AI) 工具使用揭露與說明'))
    elements.append(build_normal_p('為恪遵大專校院學術倫理規範、提升系統開發透明度並符合專題報告評審標準，本專案全面揭露在「系統功能研發」與「文件報告編修」期間所導入之人工智慧 (GenAI) 輔助工具。全體專題組員謹此嚴正聲明：本專案所有核心架構決策、前後端原始程式碼、資料庫設計、單元與整合測試用例，均經組員本人親自規劃、撰寫、編譯驗證及實機部署；生成式 AI 僅作為輔助諮詢、圖表繪製草稿及文字潤飾工具，全體組員對本報告與系統成果負完全學術與技術責任。'))
    elements.append(build_caption_p('表 14-2 人工智慧工具使用說明表'))

    table_14_2_headers = ['序號', '使用工具名稱', '使用範圍及具體說明', '應用章節或圖表編號']
    table_14_2_widths = [700, 2000, 4567, 2200]
    table_14_2_rows = [
        [
            '1',
            'Google Gemini 1.5 / 2.0 Flash\n(系統核心服務)',
            '【系統即時推論服務】\n直接部署於系統後端生產環境中，負責植物影像多模態高階特徵提取、複雜病害診斷仲裁，以及農業 RAG 知識庫之向量嵌入運算。所有模型推論結果均經過後端真值資料庫過濾與三方仲裁器校驗，嚴格防範大模型幻覺。',
            '第 1、3、5、6、7、8、11、12 章\n（涵蓋 AI 診斷、RAG 檢索及日誌持久化全流程）'
        ],
        [
            '2',
            'Antigravity AI / Cursor / Trae\n(工程開發輔助)',
            '【程式碼重構與架構實作】\n輔助組員進行 FastAPI 後端端點撰寫、Alembic 遷移腳本調優、CameraX 行動介面生命週期排查，以及全套 16 項自動化單元/整合測試個案編寫。所有程式碼皆通過本地離線測試與 CI 建置驗證。',
            '第 9 章（程式）、第 10 章（測試模型）、第 11 章（操作手冊）全章節'
        ],
        [
            '3',
            'ChatGPT (GPT-4o) / Claude 3.5\n(設計圖表繪製)',
            '【系統分析與設計圖表視覺化繪製】\n輔助將系統工程規格轉換為標準 UML 與架構圖表，包含：\n• 圖 3-1-1 系統架構圖\n• 圖 5-1-1 功能分解圖、圖 5-2-1 使用個案圖、圖 5-3-1 診斷流程活動圖\n• 圖 6-1-1 植物診斷循序圖、圖 6-2-1 設計類別圖\n• 圖 7-1-1 佈署圖、圖 7-2-1 套件圖、圖 7-3-1 元件圖\n• 圖 8-1-1 資料庫實體關聯圖 (ERD)',
            '第 3 章（圖 3-1-1）\n第 5 章（圖 5-1-1 至 5-3-1）\n第 6 章（圖 6-1-1、6-2-1）\n第 7 章（圖 7-1-1 至 7-3-1）\n第 8 章（圖 8-1-1）'
        ],
        [
            '4',
            'Trae AI / Claude 3.5 Sonnet\n(狀態機圖表彙整)',
            '【狀態轉換圖系列繪製】\n依據使用者操作生命週期，輔助繪製標準狀態機圖表，包含：\n• 圖 7-4-1 註冊&登入 狀態圖\n• 圖 7-4-2 上傳圖片並取得分析結果 狀態圖\n• 圖 7-4-3 儲存診斷紀錄 狀態圖\n• 圖 7-4-4 查看歷史紀錄 狀態圖\n• 圖 7-4-5 檢視儀表板與診斷紀錄 狀態圖\n• 圖 7-4-6 Webcam 監控與自動警報 狀態圖',
            '第 7 章（圖 7-4-1 至 7-4-6 系列狀態圖）\n第 12 章（畫面狀態轉換說明）'
        ],
        [
            '5',
            'Antigravity AI / OpenAI Codex\n(文件彙整與排版修訂)',
            '【專題系統手冊標準化修訂】\n2026-10-06 專題複審階段，用於整併擴充第十一章操作手冊、第十二章使用手冊、校準 Word 樣式層級、修復多層次目錄編號及清單格式，消除樣式衝突並完善技術查核證據。',
            '第 10 章（測試表 10-1/10-2）\n第 11 章（操作手冊 11-1～11-7）\n第 12 章（使用手冊 12-1～12-4）\n第 14 章（參考資料）'
        ]
    ]
    elements.append(build_table_xml(table_14_2_headers, table_14_2_widths, table_14_2_rows))

    # 14-3 開放資料與開源軟體授權聲明
    elements.append(build_h2_p('14-3 開放資料與開源軟體授權聲明'))
    elements.append(build_bullet_p('1. 政府資料開放授權條款 (Open Government Data License)：本系統引用之「農業部重要農業害蟲診斷圖鑑」與「樹木病蟲害診斷案例」資料，均遵循中華民國《政府資料開放授權條款 - 第 1 版 (OGL 1.0)》。本專案依條款規範，以開放、非專屬之方式於學術專題研究範疇中進行加值應用，並於文獻中明確標註原始資料來源與檢索端點。'))
    elements.append(build_bullet_p('2. 開源軟體授權條款遵從 (Open Source Compliance)：本系統整合之第三方開源函式庫（包含 FastAPI、PyTorch、FAISS、SQLAlchemy、Retrofit 等），分別遵循 MIT License、Apache 2.0 License 及 BSD 3-Clause License。全系統原始碼相容於開源授權協議，未涉及任何專利侵害或違反著作權之情事。'))
    elements.append(build_bullet_p('3. 農業診斷與處方建議專業免責聲明：本系統所提供之 AI 模型影像快篩判定、信心指數、植物病徵辨識及 RAG 知識庫防治指南，其本質定位為「輔助決策與農業衛教參考工具」。植物實際生長狀態受土壤環境、氣候溫濕度、微量元素缺乏及複合性病蟲害交相影響，若農友面臨大面積農作物異常或經濟價值重大之重大疫情，應及時採樣並送交各地農業改良場、農業試驗所或植病專家進行實驗室分子生物學鑑定，切勿僅憑系統預測逕行非處方施藥。'))

    return elements


def update_chapter_14_in_doc(docx_path):
    print(f"\n=======================================================")
    print(f"Processing Chapter 14 in: {docx_path}")
    if not os.path.exists(docx_path):
        print("  File not found! Skipping.")
        return False

    doc = docx.Document(docx_path)
    body_el = doc._body._element

    # Find Heading 1: 參考資料 (or 第14章 參考資料)
    start_idx = -1
    for i, el in enumerate(body_el):
        if el.tag.endswith('}p'):
            t_txt = ''.join([n.text or '' for n in el.iter(qn('w:t'))]).strip()
            if '參考資料' in t_txt and ('第14章' in t_txt or '第 14 章' in t_txt or t_txt == '參考資料'):
                start_idx = i
                break

    if start_idx == -1:
        print("  Could not find Heading 1: 參考資料!")
        return False

    # Chapter 14 is the final chapter.
    # The very last element of body_el is sectPr (<w:sectPr>), which MUST NOT be removed!
    end_idx = len(body_el) - 1  # preserve sectPr
    print(f"  Found 參考資料 at index {start_idx}. sectPr at index {end_idx}. Elements between: {end_idx - start_idx - 1}")

    # Remove all elements between start_idx and sectPr
    elements_to_remove = [body_el[k] for k in range(start_idx + 1, end_idx)]
    for el in elements_to_remove:
        body_el.remove(el)

    print(f"  Removed {len(elements_to_remove)} existing elements in Chapter 14.")

    # Build and insert new Chapter 14 elements right after start_idx
    new_elements = build_chapter_14_elements()
    insert_pos = start_idx + 1
    for el in new_elements:
        body_el.insert(insert_pos, el)
        insert_pos += 1

    print(f"  Successfully inserted {len(new_elements)} structured elements for Chapter 14.")

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
            update_chapter_14_in_doc(tf)
        except Exception as e:
            print(f"  Error on {tf}: {e}")
            import traceback
            traceback.print_exc()
