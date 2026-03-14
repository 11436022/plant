import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

print("目前可用模型:")

for m in genai.list_models():
    if "generateContent" in m.supported_generation_methods:
        print(f"名稱: {m.name}, 顯示名稱: {m.display_name}")