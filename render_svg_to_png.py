import os
import subprocess
from PIL import Image

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

def render_svg(svg_path, png_path, width=1600, height=900, scale=2):
    """
    Renders an SVG file to a PNG file using headless Chrome.
    """
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
  body {{ background: #ffffff; display: flex; justify-content: center; align-items: center; width: {width}px; height: {height}px; }}
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
        print(f"Rendered {png_path} ({os.path.getsize(abs_png)} bytes)")
        return True
    else:
        print(f"Failed to render {png_path}. Stderr: {res.stderr.decode('utf-8', errors='ignore')}")
        return False

if __name__ == '__main__':
    print("Testing render_svg...")
    test_svg = "documents/current_system_architecture_1.svg"
    test_png = "documents/test_out.png"
    if os.path.exists(test_svg):
        render_svg(test_svg, test_png, width=1600, height=900)
