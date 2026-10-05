import os
import subprocess
from PIL import Image

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

def render_svg(svg_path, png_path, width, height, scale=2):
    abs_svg = os.path.abspath(svg_path)
    abs_png = os.path.abspath(png_path)
    temp_html = abs_svg.replace('.svg', '_render_temp.html')
    
    svg_url = abs_svg.replace('\\', '/')
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
    with open(temp_html, 'w', encoding='utf-8') as f:
        f.write(html)
        
    cmd = [
        CHROME_PATH,
        '--headless',
        '--disable-gpu',
        f'--force-device-scale-factor={scale}',
        f'--screenshot={abs_png}',
        f'--window-size={width},{height}',
        temp_html
    ]
    
    res = subprocess.run(cmd, capture_output=True)
    if os.path.exists(temp_html):
        os.remove(temp_html)
        
    if os.path.exists(abs_png):
        im = Image.open(abs_png)
        print(f"Rendered {png_path} ({os.path.getsize(abs_png)} bytes, size={im.size})")
        return True
    else:
        print(f"Failed to render {png_path}. Stderr: {res.stderr.decode('utf-8', errors='ignore')}")
        return False

if __name__ == '__main__':
    render_svg("documents/圖/圖 3-1-1 系統架構圖.svg", "scratch/scale2x_3_1_1.png", width=1600, height=880, scale=2)
    render_svg("documents/圖/圖 5-3-1 植物病害診斷流程活動圖.svg", "scratch/scale2x_5_3_1.png", width=1260, height=880, scale=2)
    render_svg("documents/圖/圖 6-1-1 植物診斷循序圖.svg", "scratch/scale2x_6_1_1.png", width=1300, height=1180, scale=2)
    render_svg("documents/圖/圖 7-3-1 元件圖.svg", "scratch/scale2x_7_3_1.png", width=1400, height=680, scale=2)
    render_svg("documents/圖/圖 8-1-1 資料庫實體關聯圖.svg", "scratch/scale2x_8_1_1.png", width=1660, height=980, scale=2)
