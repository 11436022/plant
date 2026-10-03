import docx
import zipfile
import os
import re
import csv
import sys

# Ensure UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')

figures_dir = 'documents/圖'
tables_dir = 'documents/表'

os.makedirs(figures_dir, exist_ok=True)
os.makedirs(tables_dir, exist_ok=True)

doc_path = 'documents/系統手冊_1.docx'
doc = docx.Document(doc_path)

print("=== Extracting and Organizing Figures ===")

# Figure mapping based on document inspection
figure_meta = [
    ("圖 3-1-1 系統架構圖", "image2.png", "current_system_architecture_1.svg"),
    ("圖 4-1-1 專案時程甘特圖", "image3.png", None),
    ("圖 4-3-1 整組Github次數", "image5.png", None),
    ("圖 4-3-2 施奕安11436023 Github上傳紀錄", "image6.png", None),
    ("圖 4-3-3 周昱潤11436022 Github 上傳紀錄", "image6.png", None),
    ("圖 4-3-4 陳浩民 11436015 Github上傳紀錄", "image7.png", None),
    ("圖 4-3-5 林東建 11436014 Github上傳紀錄", "image8.png", None),
    ("圖 4-3-6 龔正源11436016 Github上傳紀錄", "image9.png", None),
    ("圖 5-1-1 功能分解圖", "image10.png", "system_fdd_1.svg"),
    ("圖 5-2-1 使用個案圖", "image11.png", "system_use_case_1.svg"),
    ("圖 5-3-1 植物病害診斷流程活動圖", "image12.png", "system_activity_diagnosis.svg"),
    ("圖 5-4-1 分析類別圖", "image13.png", "system_analysis_class.svg"),
    ("圖 5-4-2 分析物件圖", "image14.png", "system_analysis_object.svg"),
    ("圖 6-1-1 植物診斷循序圖", "image15.png", "system_sequence_diagnosis.svg"),
    ("圖 6-2-1 設計類別圖", "image16.png", "system_design_class.svg"),
    ("圖 7-1-1 佈署圖", "image17.png", "system_deployment.svg"),
    ("圖 7-2-1 套件圖", "image18.png", "system_package.svg"),
    ("圖 7-3-1 元件圖", "image19.png", "system_component.svg"),
    ("圖 7-4-1 註冊&登入 狀態圖", "image20.png", "system_state_auth.svg"),
    ("圖 7-4-2 上傳圖片並取得分析結果 狀態圖", "image21.png", "system_state_diagnosis.svg"),
    ("圖 7-4-3 儲存診斷紀錄 狀態圖", "image22.png", "system_state_save_diary.svg"),
    ("圖 7-4-4 查看歷史紀錄 狀態圖", "image24.png", "system_state_history.svg"),
    ("圖 7-4-5 檢視儀表板與診斷紀錄 狀態圖", "image24.png", "system_state_admin.svg"),
    ("圖 8-1-1 資料庫實體關聯圖", "image25.png", "system_erd.svg")
]

with zipfile.ZipFile(doc_path, 'r') as z:
    for fig_name, media_file, svg_file in figure_meta:
        # Extract PNG
        png_out = os.path.join(figures_dir, f"{fig_name}.png")
        zip_entry = f"word/media/{media_file}"
        if zip_entry in z.namelist():
            img_data = z.read(zip_entry)
            with open(png_out, 'wb') as f:
                f.write(img_data)
            print(f"Saved PNG: {png_out} ({len(img_data)} bytes)")
        
        # Copy SVG if available
        if svg_file:
            src_svg = os.path.join('documents', svg_file)
            if os.path.exists(src_svg):
                with open(src_svg, 'rb') as f:
                    svg_data = f.read()
                svg_out_named = os.path.join(figures_dir, f"{fig_name}.svg")
                svg_out_canon = os.path.join(figures_dir, svg_file)
                with open(svg_out_named, 'wb') as f:
                    f.write(svg_data)
                with open(svg_out_canon, 'wb') as f:
                    f.write(svg_data)
                print(f"Saved SVG: {svg_out_named}")

# Also copy all other SVGs in documents to figures_dir
for f in os.listdir('documents'):
    if f.endswith('.svg') or f.endswith('.png'):
        src = os.path.join('documents', f)
        dst = os.path.join(figures_dir, f)
        if not os.path.exists(dst):
            with open(src, 'rb') as s, open(dst, 'wb') as d:
                d.write(s.read())

print(f"Total files in {figures_dir}: {len(os.listdir(figures_dir))}")

print("\n=== Extracting and Organizing Tables ===")

table_titles = [
    "表 2-1-1 可行性分析表",
    "表 2-2-1 商業模式九宮格",
    "表 2-3-1 Segmentation(市場區隔)",
    "表 2-4-1 競爭力分析SWOT-TOWS",
    "表 3-2-1 系統軟硬體需求表",
    "表 3-3-1 使用標準與工具表",
    "表 4-1-1 專案時程表",
    "表 4-2-1 專案組織與分工表",
    "表 4-2-2 專題成果工作內容與貢獻度表",
    "表 5-1-1 功能需求清單表",
    "表 5-1-2 非功能需求清單表",
    "表 5-3-1 註冊",
    "表 5-3-2 Gmail信箱認證",
    "表 5-3-3 使用者登入",
    "表 5-3-4 上傳圖片並取得分析結果",
    "表 5-3-5 儲存診斷紀錄",
    "表 5-3-6 查看歷史紀錄",
    "表 5-3-7 檢視儀表板與診斷紀錄",
    "表 5-3-8 編輯診斷備忘筆記",
    "表 5-3-9 刪除診斷紀錄",
    "表 5-3-10 Webcam監控與自動警報",
    "表 5-3-11 管理Webcam警報",
    "表 5-3-12 查詢使用者列表",
    "表 5-3-13 提交診斷反饋與糾錯",
    "表 5-3-14 審核回饋與模型標註",
    "表 8-2-1 資料表-crop",
    "表 8-2-2 資料表-disease",
    "表 8-2-3 資料表-pests",
    "表 8-2-4 資料表-plant_diary",
    "表 8-2-5 資料表-user",
    "表 8-2-6 資料表-user_one_time_tokens",
    "表 8-2-7 資料表-webcam_alert",
    "表 8-2-8 資料表-diagnosis_feedback",
    "表 9-1-1 元件清單及規格描述",
    "表 11-1-1 測試策略表",
    "表 11-2-1 整合測試案例表",
    "表 12-1-1 附錄參考資料表",
    "表 13-1-1 生成式AI工具使用清單表"
]

all_tables_md = "# 系統手冊完整表格總彙整\n\n本目錄包含《植葉神醫系統手冊》全書 38 張規格表與實體欄位表。\n\n"

# Helper for markdown table formatting
def table_to_md(title, table):
    lines = [f"## {title}\n"]
    if not table.rows:
        return ""
    
    # Process rows
    matrix = []
    for row in table.rows:
        row_vals = [c.text.strip().replace('\n', '<br>') for c in row.cells]
        matrix.append(row_vals)
    
    if not matrix:
        return ""
    
    # Determine max cols
    max_cols = max(len(r) for r in matrix)
    # Header
    header = matrix[0] + [""] * (max_cols - len(matrix[0]))
    lines.append("| " + " | ".join(header) + " |")
    lines.append("| " + " | ".join(["---"] * max_cols) + " |")
    for r in matrix[1:]:
        row_padded = r + [""] * (max_cols - len(r))
        lines.append("| " + " | ".join(row_padded) + " |")
    lines.append("\n---\n")
    return "\n".join(lines)

# Helper for CSV export
def table_to_csv(filepath, table):
    with open(filepath, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        for row in table.rows:
            writer.writerow([c.text.strip().replace('\r\n', '\n').replace('\r', '\n') for c in row.cells])

# Export all tables
for idx, table in enumerate(doc.tables):
    title = table_titles[idx] if idx < len(table_titles) else f"表 {idx+1}"
    safe_title = title.replace("/", "_").replace("\\", "_")
    
    # 1. Single Markdown
    md_content = f"# {title}\n\n" + table_to_md(title, table)
    md_path = os.path.join(tables_dir, f"{safe_title}.md")
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(md_content)
    
    # 2. Single CSV (Excel-compatible UTF-8 BOM)
    csv_path = os.path.join(tables_dir, f"{safe_title}.csv")
    table_to_csv(csv_path, table)
    
    all_tables_md += table_to_md(title, table) + "\n"
    print(f"Exported Table {idx+1}: {safe_title} (.md & .csv)")

# Save All-in-one Markdown
with open(os.path.join(tables_dir, "所有表格總彙整.md"), 'w', encoding='utf-8') as f:
    f.write(all_tables_md)

# Create a clean README.md for figures directory
figures_readme = "# 系統手冊完整架構與流程圖檔總彙整\n\n本目錄包含《植葉神醫系統手冊》全書 24 張高解析度架構圖、流程圖、狀態機圖與資料庫關聯圖。\n\n| 圖號與圖名 | PNG 高解析圖檔 | SVG 向量源碼檔 |\n| :--- | :--- | :--- |\n"

for fig_name, media_file, svg_file in figure_meta:
    png_link = f"[{fig_name}.png]({fig_name}.png)"
    svg_link = f"[{fig_name}.svg]({fig_name}.svg)" if svg_file else "無 (點陣圖)"
    figures_readme += f"| {fig_name} | {png_link} | {svg_link} |\n"

with open(os.path.join(figures_dir, "所有圖檔總彙整.md"), 'w', encoding='utf-8') as f:
    f.write(figures_readme)

print(f"\nSuccessfully created documents/圖/ and documents/表/ with all assets organized!")
