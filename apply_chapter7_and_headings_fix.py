import os
import shutil
import zipfile
import docx
from lxml import etree

TARGET_DOCX = 'documents/系統手冊_1.docx'
BACKUP_DOCX = 'documents/系統手冊_1_backup_ch7.docx'

def run():
    print("--- 1. Creating Backup ---")
    shutil.copy2(TARGET_DOCX, BACKUP_DOCX)
    print(f"Backed up to {BACKUP_DOCX}")

    print("--- 2. Updating Headings & TOC (No Space) ---")
    doc = docx.Document(TARGET_DOCX)

    # 14 Chapter mapping: old/any variation -> exact standard title
    chapters = [
        ("第1章前言", "1"),
        ("第2章營運計畫", "3"),
        ("第3章系統規格", "7"),
        ("第4章專案時程與組織分工", "9"),
        ("第5章需求模型", "15"),
        ("第6章設計模型", "28"),
        ("第7章實作模型", "30"),
        ("第8章資料庫設計", "37"),
        ("第9章程式", "41"),
        ("第10章測試模型", "42"),
        ("第11章操作手冊", "44"),
        ("第12章使用手冊", "44"),
        ("第13章感想", "44"),
        ("第14章參考資料", "44"),
    ]

    # Update TOC (paragraphs 16 to 65)
    for p in doc.paragraphs[16:62]:
        text_clean = p.text.replace(' ', '').replace('\u3000', '')
        for title, page in chapters:
            prefix = title[:3] # e.g. 第1章, 第10
            core_name = title[title.find('章')+1:] # e.g. 前言, 營運計畫
            if core_name in text_clean and ('\t' in p.text) and not p.text.startswith('\t'):
                p.text = f"{title}\t{page}"
                print(f"TOC updated: {p.text}")
                break

    # Update Heading 1 in body
    h1_idx = 0
    for p in doc.paragraphs[65:]:
        if p.style.name == 'Heading 1':
            text_clean = p.text.replace(' ', '').replace('\u3000', '')
            for title, _ in chapters:
                core_name = title[title.find('章')+1:]
                if core_name in text_clean:
                    p.text = title
                    print(f"Heading 1 updated: {title}")
                    h1_idx += 1
                    break

    doc.save(TARGET_DOCX)
    print("Saved docx with standardized headings.")

    print("--- 3. Replacing State Diagrams & Extents in ZIP ---")
    replacements = {
        20: 'documents/system_state_auth.png',
        21: 'documents/system_state_diagnosis.png',
        22: 'documents/system_state_save_diary.png',
        23: 'documents/system_state_history.png',
        24: 'documents/system_state_admin.png',
    }

    # Desired dimensions (EMUs): 15.5 cm width (5580000 EMUs), height matched to aspect ratio
    rid_extents = {
        'rId33': (5580000, 3449550), # image20, 1100x680 -> 1.618
        'rId34': (5580000, 3493600), # image21, 1150x720 -> 1.597
        'rId35': (5580000, 3449550), # image22, 1100x680 -> 1.618
        'rId36': (5580000, 3449550), # image23, 1100x680 -> 1.618
        'rId37': (5580000, 3396400), # image24, 1150x700 -> 1.643
    }

    temp_zip = 'documents/temp_ch7_updated.zip'

    with zipfile.ZipFile(TARGET_DOCX, 'r') as zin, zipfile.ZipFile(temp_zip, 'w', compression=zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            filename = item.filename
            
            # Check image replacements
            is_replaced = False
            for num, png_path in replacements.items():
                target_entry = f'word/media/image{num}.png'
                if filename == target_entry:
                    print(f"Replacing {filename} with {png_path}...")
                    with open(png_path, 'rb') as f:
                        zout.writestr(item, f.read())
                    is_replaced = True
                    break
            if is_replaced:
                continue

            # Check document.xml
            if filename == 'word/document.xml':
                print("Updating document.xml extents for rId33-rId37...")
                xml_data = zin.read(filename)
                tree = etree.fromstring(xml_data)
                namespaces = {
                    'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
                    'wp': 'http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing',
                    'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
                    'pic': 'http://schemas.openxmlformats.org/drawingml/2006/picture',
                    'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
                }
                
                drawings = tree.xpath('//w:drawing', namespaces=namespaces)
                for d in drawings:
                    blips = d.xpath('.//a:blip/@r:embed', namespaces=namespaces)
                    if blips and blips[0] in rid_extents:
                        rid = blips[0]
                        new_cx, new_cy = rid_extents[rid]
                        for wp_ext in d.xpath('.//wp:extent', namespaces=namespaces):
                            wp_ext.set('cx', str(new_cx))
                            wp_ext.set('cy', str(new_cy))
                        for a_ext in d.xpath('.//a:xfrm/a:ext', namespaces=namespaces):
                            a_ext.set('cx', str(new_cx))
                            a_ext.set('cy', str(new_cy))
                        print(f"Updated {rid}: cx={new_cx}, cy={new_cy}")

                updated_xml = etree.tostring(tree, encoding='utf-8', xml_declaration=True)
                zout.writestr(item, updated_xml)
            else:
                zout.writestr(item, zin.read(filename))

    shutil.move(temp_zip, TARGET_DOCX)
    print("Successfully updated Chapter 7 diagrams and repacked docx!")

if __name__ == '__main__':
    run()
