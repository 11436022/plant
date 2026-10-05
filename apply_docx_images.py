import zipfile
import os
import shutil
import hashlib

IMG_3_1_1 = r"D:\plant_backend\scratch\scale2x_3_1_1.png"
IMG_5_3_1 = r"D:\plant_backend\scratch\scale2x_5_3_1.png"
IMG_6_1_1 = r"D:\plant_backend\scratch\scale2x_6_1_1.png"
IMG_7_3_1 = r"D:\plant_backend\scratch\scale2x_7_3_1.png"

# Also sync to antigravity scratch
brain_scratch = r"C:\Users\User\.gemini\antigravity\brain\90242f37-6ca4-4a9f-a92a-3cfdec757937\scratch"
if os.path.exists(brain_scratch):
    shutil.copy2(IMG_3_1_1, os.path.join(brain_scratch, "scale2x_3_1_1.png"))
    shutil.copy2(IMG_5_3_1, os.path.join(brain_scratch, "scale2x_5_3_1.png"))
    shutil.copy2(IMG_6_1_1, os.path.join(brain_scratch, "scale2x_6_1_1.png"))
    shutil.copy2(IMG_7_3_1, os.path.join(brain_scratch, "scale2x_7_3_1.png"))
    print("Synced all newly rendered PNGs to brain scratch directory.")

with open(IMG_3_1_1, "rb") as f:
    data_3_1_1 = f.read()

with open(IMG_5_3_1, "rb") as f:
    data_5_3_1 = f.read()

with open(IMG_6_1_1, "rb") as f:
    data_6_1_1 = f.read()

with open(IMG_7_3_1, "rb") as f:
    data_7_3_1 = f.read()

md5_3_1_1 = hashlib.md5(data_3_1_1).hexdigest()
md5_5_3_1 = hashlib.md5(data_5_3_1).hexdigest()
md5_6_1_1 = hashlib.md5(data_6_1_1).hexdigest()
md5_7_3_1 = hashlib.md5(data_7_3_1).hexdigest()

print(f"New 3-1-1: len={len(data_3_1_1)}, md5={md5_3_1_1}")
print(f"New 5-3-1: len={len(data_5_3_1)}, md5={md5_5_3_1}")
print(f"New 6-1-1: len={len(data_6_1_1)}, md5={md5_6_1_1}")
print(f"New 7-3-1: len={len(data_7_3_1)}, md5={md5_7_3_1}")

DOCX_FILES = [
    r"D:\plant_backend\documents\系統手冊_1.docx",
    r"D:\plant_backend\documents\系統手冊.docx",
    r"D:\plant_backend\documents\系統手冊前八章.docx",
    r"C:\Users\User\Downloads\系統手冊 (1).docx",
    r"C:\Users\User\Downloads\系統手冊.docx",
    r"C:\Users\User\OneDrive\文件\系統手冊.docx",
]

def update_docx(docx_path):
    if not os.path.exists(docx_path):
        print(f"File not found: {docx_path}")
        return
    
    temp_docx = docx_path + ".tmp.zip"
    try:
        with zipfile.ZipFile(docx_path, 'r') as zin, zipfile.ZipFile(temp_docx, 'w', compression=zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                if item.filename == "word/media/image2.png":
                    zout.writestr(item, data_3_1_1)
                    print(f"  [{os.path.basename(docx_path)}] Replaced word/media/image2.png (3-1-1)")
                elif item.filename == "word/media/image12.png":
                    zout.writestr(item, data_5_3_1)
                    print(f"  [{os.path.basename(docx_path)}] Replaced word/media/image12.png (5-3-1)")
                elif item.filename == "word/media/image15.png":
                    zout.writestr(item, data_6_1_1)
                    print(f"  [{os.path.basename(docx_path)}] Replaced word/media/image15.png (6-1-1)")
                elif item.filename == "word/media/image19.png":
                    zout.writestr(item, data_7_3_1)
                    print(f"  [{os.path.basename(docx_path)}] Replaced word/media/image19.png (7-3-1)")
                else:
                    zout.writestr(item, zin.read(item.filename))
        
        # Replace original
        shutil.move(temp_docx, docx_path)
        print(f"Successfully updated: {docx_path}")
    except Exception as e:
        print(f"Failed to update {docx_path}: {e}")
        if os.path.exists(temp_docx):
            os.remove(temp_docx)

for p in DOCX_FILES:
    print(f"--- Processing {p} ---")
    update_docx(p)

print("\n=== Verification ===")
for p in DOCX_FILES:
    if not os.path.exists(p):
        continue
    with zipfile.ZipFile(p, 'r') as z:
        names = z.namelist()
        m2 = hashlib.md5(z.read("word/media/image2.png")).hexdigest() if "word/media/image2.png" in names else "N/A"
        m12 = hashlib.md5(z.read("word/media/image12.png")).hexdigest() if "word/media/image12.png" in names else "N/A"
        m15 = hashlib.md5(z.read("word/media/image15.png")).hexdigest() if "word/media/image15.png" in names else "N/A"
        m19 = hashlib.md5(z.read("word/media/image19.png")).hexdigest() if "word/media/image19.png" in names else "N/A"
        print(f"{os.path.basename(p)}:\n  img2(3-1-1)={m2[:8]} (match={m2==md5_3_1_1})\n  img12(5-3-1)={m12[:8]} (match={m12==md5_5_3_1})\n  img15(6-1-1)={m15[:8]} (match={m15==md5_6_1_1})\n  img19(7-3-1)={m19[:8]} (match={m19==md5_7_3_1})")
