import os
import json
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
from PIL import Image
import torch
import torch.nn.functional as F

from app.core.config import settings
from app.db.session import get_db_connection

# 快取檔案路徑
CACHE_FILE = settings.STATIC_DIR / "visual_memory_cache.pt"


class VisualMemoryManager:
    """
    視覺特徵檢索飛輪 (Visual RAG Memory Flywheel)。
    在模型重訓的週期空窗期，利用 ConvNeXt 768 維特徵空間快速比對歷史專家標註樣本，
    實現「專家只要在後台標註一次，系統終生零延遲秒記住，即時補足未知作物先驗知識」。
    同時所有標註樣本持續沉澱為 ConvNeXt 批次重訓之正規資料集。
    """
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.records: List[Dict[str, Any]] = []
        self.embeddings: Optional[torch.Tensor] = None  # 形狀: [N, 768]
        self.last_sync_time: Optional[datetime] = None
        self._load_cache_or_build()

    def _get_feature_extractor(self):
        """取得 ConvNeXt 骨幹特徵提取器與標準轉換器。"""
        from app.services.convnext import get_convnext_model, _transform
        model = get_convnext_model()
        return model, _transform

    def extract_image_embedding(self, image_path: str) -> Optional[torch.Tensor]:
        """從指定圖片路徑提取 768 維 L2 正規化特徵向量。"""
        model, transform = self._get_feature_extractor()
        if model is None:
            return None

        p = Path(image_path)
        if not p.is_absolute():
            clean_rel = str(image_path).replace("\\", "/")
            if "static/" in clean_rel:
                clean_rel = "static/" + clean_rel.split("static/", 1)[1]
            else:
                clean_rel = clean_rel.lstrip("/")
            p = settings.BASE_DIR / clean_rel
        if not p.exists():
            return None

        try:
            img = Image.open(str(p)).convert("RGB")
            tensor = transform(img).unsqueeze(0)
            with torch.no_grad():
                feats = model.forward_features(tensor)
                embedding = model.forward_head(feats, pre_logits=True)
                emb_norm = F.normalize(embedding, p=2, dim=1)
                return emb_norm.squeeze(0).cpu()  # [768]
        except Exception as exc:
            print(f"[WARN] 視覺記憶特徵提取失敗 ({image_path}): {exc}")
            return None

    def _load_cache_or_build(self):
        """啟動時優先從磁碟快取載入特徵矩陣，若無快取則從資料庫重新構建。"""
        if CACHE_FILE.exists():
            try:
                cache_data = torch.load(str(CACHE_FILE), map_location="cpu", weights_only=False)
                self.records = cache_data.get("records", [])
                self.embeddings = cache_data.get("embeddings", None)
                self.last_sync_time = cache_data.get("last_sync_time", datetime.now())
                print(f"[OK] [VisualMemory] 視覺特徵記憶庫已從快取載入 ({len(self.records)} 筆已標註樣本)")
                return
            except Exception as exc:
                print(f"[WARN] 載入視覺特徵記憶快取失敗: {exc}，將重新構建索引")

        self.rebuild_index()

    def rebuild_index(self) -> int:
        """從資料庫讀取所有具備管理者/專家標註的回饋影像，提取特徵並持久化。"""
        conn = get_db_connection()
        db_rows = []
        try:
            import pymysql
            with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                sql = """
                    SELECT id, image_url, original_plant_name, original_disease_name,
                           corrected_plant_name, corrected_disease_name,
                           manager_corrected_plant_name, manager_corrected_disease_name,
                           created_at
                    FROM diagnosis_feedback
                    WHERE (manager_corrected_plant_name IS NOT NULL AND manager_corrected_plant_name != '')
                       OR (corrected_plant_name IS NOT NULL AND corrected_plant_name != '')
                    ORDER BY id ASC
                """
                cursor.execute(sql)
                db_rows = cursor.fetchall()
        finally:
            conn.close()

        records = []
        emb_list = []

        from app.services.ai import UNKNOWN_CROP_NAMES

        for row in db_rows:
            # 優先採用管理者標註，若無則採用回饋修正
            plant = (row.get("manager_corrected_plant_name") or row.get("corrected_plant_name") or "").strip()
            disease = (row.get("manager_corrected_disease_name") or row.get("corrected_disease_name") or row.get("original_disease_name") or "").strip()

            if not plant or plant in UNKNOWN_CROP_NAMES:
                continue

            rel_img = str(row.get("image_url", "")).replace("\\", "/")
            if "static/" in rel_img:
                clean_rel = "static/" + rel_img.split("static/", 1)[1]
            else:
                clean_rel = rel_img.lstrip("/")
            img_path = settings.BASE_DIR / clean_rel
            if not img_path.exists():
                continue

            emb = self.extract_image_embedding(str(img_path))
            if emb is not None:
                emb_list.append(emb)
                records.append({
                    "feedback_id": row["id"],
                    "image_url": clean_rel,
                    "crop_name": plant,
                    "status_name": disease or "無法判定",
                    "created_at": row.get("created_at"),
                })

        if emb_list:
            self.embeddings = torch.stack(emb_list, dim=0)  # [N, 768]
            self.records = records
            self.last_sync_time = datetime.now()
            # 儲存磁碟快取
            try:
                torch.save({
                    "records": self.records,
                    "embeddings": self.embeddings,
                    "last_sync_time": self.last_sync_time,
                }, str(CACHE_FILE))
            except Exception as e:
                print(f"[WARN] 儲存視覺記憶快取失敗: {e}")
            print(f"[OK] [VisualMemory] 視覺特徵記憶庫索引重建完成，共收錄 {len(self.records)} 筆田間專家覆核樣本！")
        else:
            self.embeddings = None
            self.records = []
            print("[INFO] 視覺特徵記憶庫暫無有效標註樣本。")

        return len(self.records)

    def add_or_update(
        self,
        feedback_id: int,
        image_url: str,
        plant_name: str,
        disease_name: Optional[str] = None
    ) -> bool:
        """當管理者在後台即時儲存一筆標註時，動態新增或更新記憶庫，零重啟立即生效！"""
        from app.services.ai import UNKNOWN_CROP_NAMES
        if not plant_name or plant_name in UNKNOWN_CROP_NAMES:
            return False

        clean_rel = str(image_url).replace("\\", "/")
        if "static/" in clean_rel:
            clean_rel = "static/" + clean_rel.split("static/", 1)[1]
        else:
            clean_rel = clean_rel.lstrip("/")
        img_path = settings.BASE_DIR / clean_rel
        if not img_path.exists():
            return False

        emb = self.extract_image_embedding(str(img_path))
        if emb is None:
            return False

        # 檢查是否已在 records 內
        existing_idx = None
        for i, r in enumerate(self.records):
            if r["feedback_id"] == feedback_id:
                existing_idx = i
                break

        if existing_idx is not None:
            self.records[existing_idx]["crop_name"] = plant_name
            self.records[existing_idx]["status_name"] = disease_name or "無法判定"
            if self.embeddings is not None:
                self.embeddings[existing_idx] = emb
        else:
            new_record = {
                "feedback_id": feedback_id,
                "image_url": image_url,
                "crop_name": plant_name,
                "status_name": disease_name or "無法判定",
                "created_at": datetime.now(),
            }
            self.records.append(new_record)
            if self.embeddings is not None:
                self.embeddings = torch.cat([self.embeddings, emb.unsqueeze(0)], dim=0)
            else:
                self.embeddings = emb.unsqueeze(0)

        # 刷新磁碟快取
        try:
            torch.save({
                "records": self.records,
                "embeddings": self.embeddings,
                "last_sync_time": datetime.now(),
            }, str(CACHE_FILE))
        except Exception:
            pass

        print(f"[VisualMemory] 樣本 ID #{feedback_id} 已成功刻錄至特徵記憶庫：【{plant_name} - {disease_name}】")
        return True

    def search(
        self,
        image_path: str,
        min_similarity: float = 0.82,
        top_k: int = 1
    ) -> Optional[Dict[str, Any]]:
        """
        在特徵空間檢索最相似的田間標註樣本。
        若最高餘弦相似度 >= min_similarity，回傳最匹配之專家標註作物與病名。
        """
        if self.embeddings is None or len(self.records) == 0:
            return None

        query_emb = self.extract_image_embedding(image_path)
        if query_emb is None:
            return None

        # 計算餘弦相似度 (兩者皆已 L2 正規化，內積即餘弦值)
        # query_emb: [768], embeddings: [N, 768]
        sims = torch.mv(self.embeddings, query_emb)  # [N]
        best_sim, best_idx = torch.max(sims, dim=0)
        best_score = float(best_sim.item())
        best_i = int(best_idx.item())

        if best_score >= min_similarity and best_i < len(self.records):
            matched = self.records[best_i]
            print(
                f"[VisualMemory 命中] 查詢影像與歷史專家樣本 #{matched['feedback_id']} "
                f"餘弦相似度達 {best_score:.4f} (>= {min_similarity:.2f})！"
                f"成功檢索先驗作物：【{matched['crop_name']}】，歷史病徵：【{matched['status_name']}】"
            )
            return {
                "hit": True,
                "similarity": round(best_score, 4),
                "crop_name": matched["crop_name"],
                "status_name": matched["status_name"],
                "feedback_id": matched["feedback_id"],
                "image_url": matched["image_url"],
            }

        return None

    def get_stats(self) -> Dict[str, Any]:
        """取得當前記憶庫統計資訊。"""
        crops = list({r["crop_name"] for r in self.records})
        return {
            "total_records": len(self.records),
            "unique_crops": crops,
            "crop_count": len(crops),
            "last_sync": self.last_sync_time.strftime("%Y-%m-%d %H:%M:%S") if self.last_sync_time else None,
        }


# 全域單例
visual_memory = VisualMemoryManager()
