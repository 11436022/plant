import os
import google.generativeai as genai
from dotenv import load_dotenv

print("--- 開始獨立測試 Gemini API 金鑰 ---")

# 載入 .env 檔案中的環境變數
load_dotenv()

# 從環境變數中讀取 API Key
api_key = os.getenv("GEMINI_API_KEY")

if not api_key or "【" in api_key:
    print("\n[錯誤] 找不到 API 金鑰，或金鑰尚未填寫。")
    print("請確認您的 .env 檔案中已正確設定 GEMINI_API_KEY。")
else:
    try:
        # 設定 API Key
        genai.configure(api_key=api_key)

        print("API Key 已設定，正在嘗試連接 Google Gemini API...")
        
        # 執行一個最簡單的 API 呼叫：列出可用的模型
        # 這是一個很好的連線測試
        models = list(genai.list_models())
        
        print("\n[成功] API 金鑰有效！連線成功！")
        
        # 為了證明我們真的拿到了資料，印出一個支援文字生成的模型名稱
        for m in models:
            if 'generateContent' in m.supported_generation_methods:
                print(f"成功取回模型，例如：{m.name}")
                break

    except Exception as e:
        print("\n[失敗] API 金鑰無效或發生錯誤！")
        print("----------------------------------------")
        print(f"錯誤類型: {type(e).__name__}")
        print(f"詳細錯誤訊息: {e}")
        print("----------------------------------------")
        print("\n請根據上方的詳細錯誤訊息，檢查您的 Google Cloud 專案設定。")

print("\n--- 測試結束 ---")