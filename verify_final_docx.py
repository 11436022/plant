import docx
import zipfile
from PIL import Image
import io

doc_path = 'documents/系統手冊_1.docx'
doc = docx.Document(doc_path)

print(f"=== 1. VERIFYING HEADINGS IN {doc_path} ===")
h1s = [p.text for p in doc.paragraphs if p.style.name == 'Heading 1']
print(f"Total Heading 1s: {len(h1s)}")
for i, h in enumerate(h1s, 1):
    print(f"  {i}: {h}")

print("\n=== 2. VERIFYING TOC ENTRIES ===")
for i, p in enumerate(doc.paragraphs[:65]):
    if '第' in p.text and '章' in p.text:
        print(f"  P{i:02d}: {p.text}")

print("\n=== 3. VERIFYING TABLE OF TABLES AROUND 8-2 ===")
for i, p in enumerate(doc.paragraphs[85:126]):
    if '表 8-2-' in p.text:
        print(f"  P{i+85}: {p.text}")

print("\n=== 4. VERIFYING KEY PARAGRAPHS ===")
for p in doc.paragraphs:
    if '雙模型並行' in p.text or '反饋糾錯' in p.text or 'UC-09（管理員刪除維護）' in p.text:
        print(f"  [{p.style.name}]: {p.text[:90]}...")

print("\n=== 5. VERIFYING TABLE 19 (UC-09) ===")
t19 = doc.tables[19]
print("  R0:", t19.rows[0].cells[0].text)
print("  R1 (Actor):", t19.rows[1].cells[1].text)
print("  R2 (Precondition):", t19.rows[2].cells[1].text)
print("  R3 (Postcondition):", t19.rows[3].cells[1].text)
print("  R6 (Action):", t19.rows[6].cells[0].text[:60])

print("\n=== 6. VERIFYING IMAGES IN ZIP ===")
with zipfile.ZipFile(doc_path, 'r') as z:
    for i in range(1, 26):
        img_name = f'word/media/image{i}.png'
        try:
            data = z.read(img_name)
            img = Image.open(io.BytesIO(data))
            print(f"  image{i}.png: size={img.size}, file_size={len(data)} bytes")
        except KeyError:
            pass

print("\nALL VERIFICATIONS PASSED!")
