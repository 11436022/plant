import os

from dotenv import load_dotenv
from google import genai


def main() -> None:
    """列出目前 Gemini API Key 可使用的內容生成模型。"""

    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise SystemExit("找不到 GEMINI_API_KEY，請先設定 .env。")

    client = genai.Client(api_key=api_key)
    print("目前可用模型：")
    for model in client.models.list():
        actions = {
            str(action).replace("_", "").lower()
            for action in (model.supported_actions or [])
        }
        if "generatecontent" in actions:
            print(f"模型名稱: {model.name}, 顯示名稱: {model.display_name}")


if __name__ == "__main__":
    main()
