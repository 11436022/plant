import json
import os
from pathlib import Path

import docx
import faiss
import numpy as np
from dotenv import load_dotenv
from google import genai
from google.genai import types

# --- 設定 ---
# 知識庫來源目錄
DOCUMENTS_DIR = Path("documents")
# 向量索引儲存路徑
FAISS_INDEX_PATH = "knowledge_base.faiss"
# 內容儲存路徑
CONTENT_PATH = "knowledge_content.json"
# Google Embedding 模型
EMBEDDING_MODEL = "gemini-embedding-001"
EMBEDDING_DIMENSION = 768
EMBEDDING_BATCH_SIZE = 100


def load_documents():
    """從 documents 資料夾讀取所有 .docx 檔案內容。"""
    print(f"🔍 開始從 '{DOCUMENTS_DIR}' 資料夾讀取 .docx 檔案...")
    all_paragraphs = []
    if not DOCUMENTS_DIR.is_dir():
        print(f"⚠️ 警告：找不到 '{DOCUMENTS_DIR}' 資料夾。")
        return []

    doc_files = list(DOCUMENTS_DIR.glob("*.docx"))
    if not doc_files:
        print(f"⚠️ 警告：在 '{DOCUMENTS_DIR}' 中沒有找到任何 .docx 檔案。")
        return []

    for doc_path in doc_files:
        try:
            doc = docx.Document(doc_path)
            # 簡單的切割邏輯：將每個段落視為一個獨立的知識片段
            # 未來可以優化：例如根據標題或空行來合併相關段落
            for para in doc.paragraphs:
                text = para.text.strip()
                if text:  # 忽略空段落
                    all_paragraphs.append(text)
            print(f"  - 已成功讀取檔案：{doc_path.name}")
        except Exception as e:
            print(f"❌ 讀取檔案 '{doc_path.name}' 時發生錯誤：{e}")

    print(f"✅ 檔案讀取完成，共讀取到 {len(all_paragraphs)} 個段落。")
    return all_paragraphs


def build_and_save_knowledge_base(paragraphs: list[str]):
    """為段落產生向量，並建立與儲存 FAISS 索引。"""
    if not paragraphs:
        print("🚫 沒有內容可供建立知識庫，程序中止。")
        return

    print("\n🔄 開始為文件內容產生向量 (Embeddings)...")
    print(f"   (這可能需要一些時間，取決於文件數量和網路速度)")

    try:
        client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        embeddings = []
        for start in range(0, len(paragraphs), EMBEDDING_BATCH_SIZE):
            batch = paragraphs[start:start + EMBEDDING_BATCH_SIZE]
            response = client.models.embed_content(
                model=EMBEDDING_MODEL,
                contents=batch,
                config=types.EmbedContentConfig(
                    task_type="RETRIEVAL_DOCUMENT",
                    title="植物知識庫文件",
                    output_dimensionality=EMBEDDING_DIMENSION,
                ),
            )
            embeddings.extend(item.values for item in response.embeddings)

        if len(embeddings) != len(paragraphs):
            raise RuntimeError("Embedding count does not match the number of document paragraphs.")
        print("✅ 向量產生完成！")

        # 建立 FAISS 索引
        print("\n🔄 開始建立 FAISS 向量索引...")
        vectors = np.asarray(embeddings, dtype=np.float32)
        faiss.normalize_L2(vectors)
        index = faiss.IndexFlatIP(EMBEDDING_DIMENSION)
        index.add(vectors)
        print(f"   - 索引維度: {EMBEDDING_DIMENSION}")
        print(f"   - 索引中的向量總數: {index.ntotal}")

        # 儲存索引和內容
        faiss.write_index(index, FAISS_INDEX_PATH)
        print(f"✅ FAISS 索引已成功儲存至 '{FAISS_INDEX_PATH}'")

        with open(CONTENT_PATH, "w", encoding="utf-8") as f:
            json.dump(paragraphs, f, ensure_ascii=False, indent=2)
        print(f"✅ 文件內容已成功儲存至 '{CONTENT_PATH}'")

    except Exception as e:
        print(f"❌ 在建立知識庫時發生嚴重錯誤：{e}")
        print("   - 請檢查您的 Google API 金鑰 ('GEMINI_API_KEY') 是否已在 .env 檔案中正確設定。")
        print("   - 請確認已安裝所有必要的套件：pip install -r requirements.txt")


if __name__ == "__main__":
    print("--- RAG 知識庫建立程序 ---")
    # 載入 .env 檔案中的環境變數 (特別是 GEMINI_API_KEY)
    load_dotenv()

    if not os.getenv("GEMINI_API_KEY"):
        print("\n🛑 錯誤：找不到 'GEMINI_API_KEY' 環境變數。")
        print("   請在專案根目錄的 .env 檔案中設定您的 Google API 金鑰。")
        print("   例如：GEMINI_API_KEY='AIzaSy...'\n")
    else:
        documents = load_documents()
        build_and_save_knowledge_base(documents)
        print("\n--- 程序完成 ---")
