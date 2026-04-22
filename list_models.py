import os

import google.generativeai as genai
from dotenv import load_dotenv

# 載入 Gemini 金鑰並列出可生成內容的模型。
load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

print("目前可用模型：")

for m in genai.list_models():
    if "generateContent" in m.supported_generation_methods:
        print(f"模型名稱: {m.name}, 顯示名稱: {m.display_name}")
