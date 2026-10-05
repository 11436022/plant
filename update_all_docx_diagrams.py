import os
import zipfile
import shutil
import hashlib
import docx

IMG_MAP = {
    '3-1-1': r"D:\plant_backend\scratch\scale2x_3_1_1.png",
    '5-3-1': r"D:\plant_backend\scratch\scale2x_5_3_1.png",
    '6-1-1': r"D:\plant_backend\scratch\scale2x_6_1_1.png",
    '7-3-1': r"D:\plant_backend\scratch\scale2x_7_3_1.png",
    '8-1-1': r"D:\plant_backend\scratch\scale2x_8_1_1.png",
}

# Sync to brain scratch
brain_scratch = r"C:\Users\User\.gemini\antigravity\brain\90242f37-6ca4-4a9f-a92a-3cfdec757937\scratch"
if os.path.exists(brain_scratch):
    for fig, img_path in IMG_MAP.items():
        if os.path.exists(img_path):
            shutil.copy2(img_path, os.path.join(brain_scratch, os.path.basename(img_path)))
    print("Synced all newly rendered PNGs to brain scratch directory.")

# Load image data and md5
IMG_DATA = {}
IMG_MD5 = {}
for fig, img_path in IMG_MAP.items():
    with open(img_path, "rb") as f:
        d = f.read()
        IMG_DATA[fig] = d
        IMG_MD5[fig] = hashlib.md5(d).hexdigest()
    print(f"Fig {fig}: file={os.path.basename(img_path)}, len={len(d)}, md5={IMG_MD5[fig]}")

DOCX_FILES = [
    r"D:\plant_backend\documents\系統手冊_1.docx",
    r"D:\plant_backend\documents\系統手冊.docx",
    r"D:\plant_backend\documents\系統手冊前八章.docx",
    r"C:\Users\User\Downloads\系統手冊 (1).docx",
    r"C:\Users\User\Downloads\系統手冊.docx",
    r"C:\Users\User\OneDrive\文件\系統手冊.docx",
]

def get_docx_mapping(docx_path):
    doc = docx.Document(docx_path)
    mapping = {}
    for f in IMG_MAP.keys():
        for i, para in enumerate(doc.paragraphs):
            # Caption or figure reference paragraph (ignore TOC before paragraph 50)
            if f in para.text and i > 45:
                for j in range(max(0, i-3), min(len(doc.paragraphs), i+2)):
                    for rId in doc.part.rels:
                        if rId in doc.paragraphs[j]._p.xml and 'image' in doc.part.rels[rId].target_ref:
                            # docx rel target_ref is e.g. "media/image2.png" -> zip entry is "word/media/image2.png"
                            zip_path = "word/" + doc.part.rels[rId].target_ref.lstrip('/')
                            mapping[zip_path] = f
                            break
                    if f in [mapping[k] for k in mapping]: break
            if f in [mapping[k] for k in mapping]: break
    return mapping

for docx_path in DOCX_FILES:
    if not os.path.exists(docx_path):
        print(f"Skipping (not found): {docx_path}")
        continue
    
    print(f"\n==========================================")
    print(f"Processing: {docx_path}")
    doc_map = get_docx_mapping(docx_path)
    for zip_entry, fig in doc_map.items():
        print(f"  Detected mapping: {fig} -> {zip_entry}")
    
    temp_docx = docx_path + ".tmp.zip"
    try:
        with zipfile.ZipFile(docx_path, 'r') as zin, zipfile.ZipFile(temp_docx, 'w', compression=zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                if item.filename in doc_map:
                    fig = doc_map[item.filename]
                    zout.writestr(item, IMG_DATA[fig])
                    print(f"  [REPLACED] {item.filename} with Fig {fig}")
                else:
                    zout.writestr(item, zin.read(item.filename))
        
        shutil.move(temp_docx, docx_path)
        print(f"  Successfully updated: {docx_path}")
    except Exception as e:
        print(f"  Error updating {docx_path}: {e}")
        if os.path.exists(temp_docx):
            os.remove(temp_docx)

print("\n================ VERIFICATION ================")
for docx_path in DOCX_FILES:
    if not os.path.exists(docx_path): continue
    print(f"\nVerifying {os.path.basename(docx_path)}:")
    doc_map = get_docx_mapping(docx_path)
    with zipfile.ZipFile(docx_path, 'r') as z:
        for zip_entry, fig in doc_map.items():
            if zip_entry in z.namelist():
                actual_md5 = hashlib.md5(z.read(zip_entry)).hexdigest()
                expected_md5 = IMG_MD5[fig]
                match = (actual_md5 == expected_md5)
                print(f"  Fig {fig} ({zip_entry}): actual={actual_md5[:8]}, expected={expected_md5[:8]}, MATCH={match}")
            else:
                print(f"  Fig {fig} ({zip_entry}): NOT FOUND IN ZIP")
