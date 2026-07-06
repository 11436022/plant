import json
from pathlib import Path

import faiss
import numpy as np
import google.generativeai as genai
from google.generativeai import embed_content

# --- 設定 ---
FAISS_INDEX_PATH = Path("knowledge_base.faiss")
CONTENT_PATH = Path("knowledge_content.json")
EMBEDDING_MODEL = "models/text-embedding-004"

# --- 全域變數，儲存載入的知識庫 ---
faiss_index = None
knowledge_content = []


def load_knowledge_base():
    """
    在應用程式啟動時載入 FAISS 索引和內容檔案。
    """
    global faiss_index, knowledge_content
    print("--- 載入 RAG 知識庫 ---")

    if not FAISS_INDEX_PATH.exists() or not CONTENT_PATH.exists():
        print("⚠️ 警告：找不到知識庫檔案 (knowledge_base.faiss 或 knowledge_content.json)。")
        print("   請先執行 build_knowledge_base.py 來建立知識庫。")
        print("   RAG 功能將無法使用。")
        faiss_index = None
        knowledge_content = []
        return

    try:
        faiss_index = faiss.read_index(str(FAISS_INDEX_PATH))
        with open(CONTENT_PATH, "r", encoding="utf-8") as f:
            knowledge_content = json.load(f)
        print(f"✅ 知識庫載入成功！索引中有 {faiss_index.ntotal} 個向量。")
    except Exception as e:
        print(f"❌ 載入知識庫時發生錯誤：{e}")
        faiss_index = None
        knowledge_content = []


def search_knowledge_base(query: str, k: int = 3) -> str:
    """
    根據查詢字串搜尋知識庫，並回傳最相關的內容。

    :param query: 使用者的查詢或圖片的初步描述。
    :param k: 要回傳的相關片段數量。
    :return: 組合好的上下文文字，如果知識庫未載入則為空字串。
    """
    if faiss_index is None or not knowledge_content:
        print(" RAG Search: 知識庫未載入，跳過搜尋。")
        return ""

    try:
        # 1. 為查詢產生向量
        response = embed_content(
            model=EMBEDDING_MODEL,
            content=query,
            task_type="retrieval_query",
            title="植物診斷查詢",
        )
        query_embedding = response["embedding"]

        # 2. 在 FAISS 中搜尋最相似的 k 個向量
        distances, indices = faiss_index.search(np.array([query_embedding], dtype=np.float32), k)

        # 3. 組合上下文
        context = []
        print(f" RAG Search: 找到 {len(indices[0])} 個相關片段。")
        for i in indices[0]:
            if 0 <= i < len(knowledge_content):
                context.append(knowledge_content[i])

        return "\n\n".join(context)

    except Exception as e:
        print(f"❌ 在搜尋知識庫時發生錯誤：{e}")
        return ""