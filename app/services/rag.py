import json
import hashlib
import os
from pathlib import Path

import faiss
import numpy as np
from google import genai
from google.genai import types

from app.core.config import settings

# --- 設定 ---
FAISS_INDEX_PATH = Path("knowledge_base.faiss")
CONTENT_PATH = Path("knowledge_content.json")
EMBEDDING_MODEL = "gemini-embedding-001"
EMBEDDING_DIMENSION = 768

# --- 全域變數，儲存載入的知識庫 ---
faiss_index = None
knowledge_content = []
_client = None


def get_gemini_client():
    global _client
    if _client is not None:
        return _client
    api_key = getattr(settings, "GEMINI_API_KEY", None) or os.getenv("GEMINI_API_KEY")
    if api_key:
        _client = genai.Client(api_key=api_key)
    return _client


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
            manifest = json.load(f)
        if not isinstance(manifest, dict) or manifest.get("schema_version") != 2:
            raise ValueError("Legacy or undocumented RAG corpus; rebuild from reference records.")
        entries = manifest.get("entries", [])
        if (manifest.get("embedding_model") != EMBEDDING_MODEL
                or manifest.get("dimension") != EMBEDDING_DIMENSION
                or manifest.get("index_sha256") != hashlib.sha256(FAISS_INDEX_PATH.read_bytes()).hexdigest()
                or not isinstance(entries, list) or faiss_index.ntotal != len(entries)
                or not all(isinstance(entry, dict) and all(entry.get(key) for key in
                           ("text", "source_name", "source_url", "source_record_id")) for entry in entries)):
            raise ValueError("RAG index and source manifest do not match.")
        knowledge_content = [entry["text"] for entry in entries]
        if (
            faiss_index.d != EMBEDDING_DIMENSION
            or faiss_index.metric_type != faiss.METRIC_INNER_PRODUCT
        ):
            print("⚠️ RAG 索引版本不相容，請重新執行 build_knowledge_base.py。")
            faiss_index = None
            knowledge_content = []
            return
        print(f"✅ 知識庫載入成功！索引中有 {faiss_index.ntotal} 個向量。")
    except Exception as e:
        print(f"❌ 載入知識庫時發生錯誤：{e}")
        faiss_index = None
        knowledge_content = []


def search_knowledge_base(query: str, k: int = 3, min_score: float = 0.68) -> str:
    """
    根據查詢字串搜尋知識庫，並回傳最相關且有實質意義的內容。
    若知識庫未載入、無實質條目或相似度不足，回傳空字串。

    :param query: 使用者的查詢或圖片的初步描述。
    :param k: 要回傳的相關片段數量。
    :param min_score: 最低向量內積相似度門檻。
    :return: 組合好的上下文文字，若無高相關內容則回傳空字串。
    """
    if faiss_index is None or not knowledge_content:
        return ""

    client = get_gemini_client()
    if client is None:
        print("⚠️ RAG Search: 未設定 GEMINI_API_KEY，跳過向量搜尋。")
        return ""

    try:
        # 1. 為查詢產生向量
        response = client.models.embed_content(
            model=EMBEDDING_MODEL,
            contents=query,
            config=types.EmbedContentConfig(
                task_type="RETRIEVAL_QUERY",
                output_dimensionality=EMBEDDING_DIMENSION,
            ),
        )
        query_embedding = np.asarray([response.embeddings[0].values], dtype=np.float32)
        faiss.normalize_L2(query_embedding)

        # 2. 在 FAISS 中搜尋最相似的 k 個向量
        result_count = min(k, faiss_index.ntotal)
        if result_count == 0:
            return ""
        scores, indices = faiss_index.search(query_embedding, result_count)

        # 3. 組合實質上下文並過濾無效雜訊
        context = []
        query_tokens = [tok.strip() for tok in query.split() if len(tok.strip()) >= 2]

        for score, i in zip(scores[0], indices[0]):
            if 0 <= i < len(knowledge_content):
                item = knowledge_content[i].strip()
                # 排除過短片段（< 40 字元）或純表格目錄標題等無效雜訊
                if len(item) < 40:
                    continue
                if item.startswith("表 ") or "資料表-" in item or "專題設計" in item or "專題報告" in item:
                    continue

                # 必須有足夠相似度，或者命中關鍵詞
                has_keyword = any(tok in item for tok in query_tokens)
                if score >= min_score or (has_keyword and score >= 0.55):
                    context.append(item)

        if not context:
            print(f"ℹ️ RAG Search: 查詢 '{query}' 檢索結果無實質農業關聯內容，視為未命中。")
            return ""

        print(f"✅ RAG Search: 找到 {len(context)} 個高相關實質片段。")
        return "\n\n".join(context)

    except Exception as e:
        print(f"❌ 在搜尋知識庫時發生錯誤：{e}")
        return ""
