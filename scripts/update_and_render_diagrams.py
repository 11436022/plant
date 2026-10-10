import os
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
if not os.path.exists(CHROME_PATH):
    raise FileNotFoundError(f"找不到 Chrome: {CHROME_PATH}")

SCRATCH_DIR = ROOT_DIR / "scratch"
SCRATCH_DIR.mkdir(parents=True, exist_ok=True)

# 1. 定義要修改與渲染的 SVG 圖表清單
DIAGRAMS = [
    {
        "id": "3-1-1",
        "svg_main": ROOT_DIR / "documents" / "圖" / "圖 3-1-1 系統架構圖.svg",
        "svg_synced": [
            ROOT_DIR / "documents" / "current_system_architecture.svg",
            ROOT_DIR / "documents" / "current_system_architecture_1.svg",
        ],
        "png_out": SCRATCH_DIR / "scale2x_3_1_1.png",
        "docx_media": "word/media/image2.png",
        "width": 1600,
        "height": 880,
    },
    {
        "id": "6-1-1",
        "svg_main": ROOT_DIR / "documents" / "圖" / "圖 6-1-1 植物診斷循序圖.svg",
        "svg_synced": [
            ROOT_DIR / "documents" / "system_sequence_diagnosis.svg",
        ],
        "png_out": SCRATCH_DIR / "scale2x_6_1_1.png",
        "docx_media": "word/media/image14.png",
        "width": 1300,
        "height": 1180,
    },
    {
        "id": "7-1-1",
        "svg_main": ROOT_DIR / "documents" / "圖" / "圖 7-1-1 佈署圖.svg",
        "svg_synced": [
            ROOT_DIR / "documents" / "system_deployment.svg",
        ],
        "png_out": SCRATCH_DIR / "scale2x_7_1_1.png",
        "docx_media": "word/media/image16.png",
        "width": 1200,
        "height": 750,
    },
    {
        "id": "7-2-1",
        "svg_main": ROOT_DIR / "documents" / "圖" / "圖 7-2-1 套件圖.svg",
        "svg_synced": [
            ROOT_DIR / "documents" / "system_package.svg",
        ],
        "png_out": SCRATCH_DIR / "scale2x_7_2_1.png",
        "docx_media": "word/media/image17.png",
        "width": 1280,
        "height": 860,
    },
    {
        "id": "7-3-1",
        "svg_main": ROOT_DIR / "documents" / "圖" / "圖 7-3-1 元件圖.svg",
        "svg_synced": [
            ROOT_DIR / "documents" / "system_component.svg",
        ],
        "png_out": SCRATCH_DIR / "scale2x_7_3_1.png",
        "docx_media": "word/media/image18.png",
        "width": 1400,
        "height": 680,
    },
    {
        "id": "7-4-2",
        "svg_main": ROOT_DIR / "documents" / "圖" / "圖 7-4-2 上傳圖片並取得分析結果 狀態圖.svg",
        "svg_synced": [
            ROOT_DIR / "documents" / "system_state_diagnosis.svg",
        ],
        "png_out": SCRATCH_DIR / "scale2x_7_4_2.png",
        "docx_media": "word/media/image20.png",
        "width": 1150,
        "height": 720,
    },
]


def update_svg_content(path: Path) -> int:
    if not path.exists():
        return 0
    content = path.read_text(encoding="utf-8")
    new_content, count = re.subn(r"Gemini\s+2\.5(?:\s+Flash)?", "Gemini 3.8 Flash", content, flags=re.IGNORECASE)
    if count > 0:
        path.write_text(new_content, encoding="utf-8")
        print(f"  [SVG更新] {path.name}: 替換了 {count} 處 'Gemini 2.5' 為 'Gemini 3.8 Flash'")
    return count


def render_svg_to_png(svg_path: Path, png_path: Path, width: int, height: int, scale: int = 2):
    abs_svg = str(svg_path.resolve())
    abs_png = str(png_path.resolve())
    temp_html = svg_path.with_name(f"{svg_path.stem}_render_temp.html")
    svg_url = abs_svg.replace("\\", "/")

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ background: #ffffff; width: {width}px; height: {height}px; overflow: hidden; }}
  img {{ width: {width}px; height: {height}px; display: block; }}
</style>
</head>
<body>
  <img src="file:///{svg_url}" />
</body>
</html>
"""
    temp_html.write_text(html, encoding="utf-8")
    cmd = [
        CHROME_PATH,
        "--headless",
        "--disable-gpu",
        f"--force-device-scale-factor={scale}",
        f"--screenshot={abs_png}",
        f"--window-size={width},{height}",
        str(temp_html),
    ]

    res = subprocess.run(cmd, capture_output=True)
    if temp_html.exists():
        temp_html.unlink()

    if png_path.exists():
        size = png_path.stat().st_size
        print(f"  [渲染成功] {png_path.name} ({size:,} bytes)")
        return True
    else:
        print(f"  [渲染失敗] {png_path.name}. 錯誤: {res.stderr.decode('utf-8', errors='ignore')}")
        return False


def main():
    print("🎨 步驟 1：更新 SVG 原始圖檔文字為 Gemini 3.8 Flash...")
    for diag in DIAGRAMS:
        update_svg_content(diag["svg_main"])
        for synced in diag["svg_synced"]:
            update_svg_content(synced)

    print("\n🖥️ 步驟 2：使用 Headless Chrome 重新渲染高解析度 PNG...")
    rendered_data = {}
    for diag in DIAGRAMS:
        render_svg_to_png(
            diag["svg_main"],
            diag["png_out"],
            diag["width"],
            diag["height"],
            scale=2,
        )
        if diag["png_out"].exists():
            rendered_data[diag["docx_media"]] = diag["png_out"].read_bytes()

    print("\n📦 步驟 3：將新圖片替換入 documents/系統手冊_1.docx...")
    docx_path = ROOT_DIR / "documents" / "系統手冊_1.docx"
    temp_docx = docx_path.with_name("系統手冊_1_img_temp.docx")

    with zipfile.ZipFile(docx_path, "r") as zin:
        with zipfile.ZipFile(temp_docx, "w", compression=zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                if item.filename in rendered_data:
                    zout.writestr(item, rendered_data[item.filename])
                    print(f"  [圖片替換] 成功更新 {item.filename}")
                else:
                    zout.writestr(item, zin.read(item.filename))

    temp_docx.replace(docx_path)
    print(f"💾 系統手冊_1.docx 圖片庫已成功覆寫更新！")

    # 驗證
    import docx
    doc = docx.Document(docx_path)
    print(f"✅ 檔案驗證通過：{docx_path.name} 可正常開啟，共 {len(doc.paragraphs)} 段落")


if __name__ == "__main__":
    main()
