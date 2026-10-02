"""Build retrieval context from traceable agricultural records, not project manuals."""
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import faiss
import numpy as np
from dotenv import load_dotenv
from google import genai
from google.genai import types

REFERENCE_PATH = Path("data.json")
FAISS_INDEX_PATH = "knowledge_base.faiss"
CONTENT_PATH = "knowledge_content.json"
EMBEDDING_MODEL = "gemini-embedding-001"
EMBEDDING_DIMENSION = 768
EMBEDDING_BATCH_SIZE = 100


def load_documents():
    """Keep the existing entry point, but accept only source-bearing records."""
    data = json.loads(REFERENCE_PATH.read_text(encoding="utf-8"))
    entries = []
    for table, name_field in (("diseases", "disease_name"), ("pests", "pest_name")):
        for row in data.get(table, []):
            required = ("crop_name", name_field, "description", "treatment", "source_name", "source_url", "source_record_id")
            if not all(str(row.get(field) or "").strip() for field in required):
                continue
            text = "\n".join([
                f"作物：{row['crop_name']}；病蟲害：{row[name_field]}",
                f"症狀參考：{row['description']}",
                f"處理參考：{row['treatment']}",
                f"來源：{row['source_name']}；紀錄：{row['source_record_id']}；網址：{row['source_url']}",
                "來源欄位完整不代表辨識正確或現行處方經專業核准。",
            ])
            entries.append({"text": text, "source_name": row["source_name"], "source_url": row["source_url"],
                            "source_record_id": row["source_record_id"]})
    return entries


def build_and_save_knowledge_base(entries):
    if not entries:
        raise ValueError("No traceable agricultural records available; existing index was not changed.")
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    embeddings = []
    for start in range(0, len(entries), EMBEDDING_BATCH_SIZE):
        batch = entries[start:start + EMBEDDING_BATCH_SIZE]
        response = client.models.embed_content(
            model=EMBEDDING_MODEL, contents=[entry["text"] for entry in batch],
            config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT", title="植物病蟲害參考資料",
                                           output_dimensionality=EMBEDDING_DIMENSION),
        )
        embeddings.extend(item.values for item in response.embeddings)
    vectors = np.asarray(embeddings, dtype=np.float32)
    if vectors.shape != (len(entries), EMBEDDING_DIMENSION) or not np.isfinite(vectors).all():
        raise RuntimeError("Embedding dimensions or values are invalid.")
    faiss.normalize_L2(vectors)
    index = faiss.IndexFlatIP(EMBEDDING_DIMENSION)
    index.add(vectors)
    index_path, content_path = Path(FAISS_INDEX_PATH), Path(CONTENT_PATH)
    index_tmp, content_tmp = index_path.with_suffix(".faiss.tmp"), content_path.with_suffix(".json.tmp")
    try:
        faiss.write_index(index, str(index_tmp))
        manifest = {
            "schema_version": 2, "embedding_model": EMBEDDING_MODEL, "dimension": EMBEDDING_DIMENSION,
            "built_at": datetime.now(timezone.utc).isoformat(),
            "source_file": REFERENCE_PATH.name,
            "source_sha256": hashlib.sha256(REFERENCE_PATH.read_bytes()).hexdigest(),
            "index_sha256": hashlib.sha256(index_tmp.read_bytes()).hexdigest(),
            "entries": entries,
        }
        content_tmp.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(index_tmp, index_path)
        os.replace(content_tmp, content_path)
    finally:
        index_tmp.unlink(missing_ok=True)
        content_tmp.unlink(missing_ok=True)
    print(f"Built {len(entries)} source-bearing reference entries.")


if __name__ == "__main__":
    load_dotenv()
    if not os.getenv("GEMINI_API_KEY"):
        raise SystemExit("GEMINI_API_KEY is required to build embeddings.")
    build_and_save_knowledge_base(load_documents())
