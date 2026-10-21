import os
import re
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

# 髒資料黑名單（嚴格攔截非專業測試字串，防止模型訓練與視覺記憶被污染）
DIRTY_TERMS_BLACKLIST = {
    "123", "1234", "test", "測試", "none", "null", "asdf", "abc", "unknown", 
    "未知", "無", "0", "n/a", "na", "nan", "nil", "undefined", "待查", "待審核",
    "測試用", "假資料", "隨便", "亂打", "xxx", "yyy", "zzz", "111", "999"
}


def is_valid_disease_status(status_name: Optional[str]) -> bool:
    """
    【資料清洗與防污染過濾器】
    驗證輸入的病害/健康狀態是否為合法的農業標籤，阻擋髒資料（如 123、測試、純數字）進入訓練集與記憶庫。
    """
    if not status_name:
        return False
    clean = str(status_name).strip()
    if len(clean) < 2 or len(clean) > 50:
        return False
    # 純數字或含符號的純數字直接攔截 (例如 123, 999, 1.2.3)
    if clean.isdigit() or re.match(r"^[\d\s\.,_\-]+$", clean):
        return False
    # 必須包含中文字或英文字母
    if not re.search(r"[\u4e00-\u9fa5a-zA-Z]", clean):
        return False
    # 黑名單完全匹配
    if clean.lower() in DIRTY_TERMS_BLACKLIST:
        return False
    # 前綴黑名單 (例如 test1, 123測試)
    if any(clean.lower().startswith(b) and len(clean) <= len(b) + 3 for b in ["test", "123", "測試"]):
        return False
    return True


def is_valid_crop_name(crop_name: Optional[str]) -> bool:
    """驗證作物名稱是否合法，防止髒資料與未定名標籤入庫"""
    from app.services.ai import UNKNOWN_CROP_NAMES
    if not crop_name:
        return False
    clean = str(crop_name).strip()
    if len(clean) < 2 or len(clean) > 30:
        return False
    if clean.isdigit() or re.match(r"^[\d\s\.,_\-]+$", clean):
        return False
    if clean in UNKNOWN_CROP_NAMES or clean.lower() in DIRTY_TERMS_BLACKLIST:
        return False
    if not re.search(r"[\u4e00-\u9fa5a-zA-Z]", clean):
        return False
    return True


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
        """從資料庫讀取所有具備管理者/專家標註的回饋影像與病歷校正，經防污染過濾後提取特徵並持久化。"""
        conn = get_db_connection()
        db_rows = []
        diary_rows = []
        try:
            import pymysql
            with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                # 1. 載入使用者回饋中心專家標註 (UC-14)
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

                # 2. 載入植物病歷簿中經專家校正且具備圖片之樣本 (UC-08)
                sql_diary = """
                    SELECT d.id, d.image_url, d.status_name, d.user_corrected_status, d.created_at, c.crop_name
                    FROM plant_diary d
                    LEFT JOIN crop c ON d.crop_id = c.crop_id
                    WHERE d.user_corrected_status IS NOT NULL 
                      AND d.user_corrected_status != ''
                      AND d.image_url IS NOT NULL
                    ORDER BY d.id ASC
                """
                cursor.execute(sql_diary)
                diary_rows = cursor.fetchall()
        except Exception as err:
            print(f"[WARN] 讀取標註樣本異常: {err}")
        finally:
            conn.close()

        records = []
        emb_list = []

        # 處理 feedback 標註樣本
        for row in db_rows:
            plant = (row.get("manager_corrected_plant_name") or row.get("corrected_plant_name") or "").strip()
            disease = (row.get("manager_corrected_disease_name") or row.get("corrected_disease_name") or row.get("original_disease_name") or "").strip()

            # 嚴格防污染清洗：非合法作物或病名直接過濾
            if not is_valid_crop_name(plant) or not is_valid_disease_status(disease):
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
                    "unique_key": f"feedback_{row['id']}",
                    "feedback_id": row["id"],
                    "source": "feedback",
                    "image_url": clean_rel,
                    "crop_name": plant,
                    "status_name": disease or "無法判定",
                    "created_at": row.get("created_at"),
                })

        # 處理 diary 專家校正樣本
        for row in diary_rows:
            plant = (row.get("crop_name") or "").strip()
            disease = (row.get("user_corrected_status") or "").strip()

            # 若作物名稱缺失，嘗試從原病害標記或病名反推
            if not plant and disease:
                for pv_data in [
                    {"crop": "番茄", "keywords": ["番茄", "晚疫", "早疫", "黃化捲葉"]},
                    {"crop": "馬鈴薯", "keywords": ["馬鈴薯"]},
                    {"crop": "柑橘", "keywords": ["柑橘", "黃龍病", "葉蟎"]},
                    {"crop": "蘋果", "keywords": ["蘋果", "黑星病"]},
                    {"crop": "玉米", "keywords": ["玉米", "銹病", "煤紋病"]},
                    {"crop": "葡萄", "keywords": ["葡萄", "黑腐病"]},
                    {"crop": "草莓", "keywords": ["草莓"]},
                ]:
                    if any(k in disease or k in (row.get("status_name") or "") for k in pv_data["keywords"]):
                        plant = pv_data["crop"]
                        break

            # 嚴格防污染清洗：非合法作物或病名直接過濾（例如 123、測試、純數字）
            if not is_valid_crop_name(plant) or not is_valid_disease_status(disease):
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
                    "unique_key": f"diary_{row['id']}",
                    "feedback_id": -row["id"],
                    "diary_id": row["id"],
                    "source": "diary",
                    "image_url": clean_rel,
                    "crop_name": plant,
                    "status_name": disease,
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
            if not self.records and CACHE_FILE.exists():
                try:
                    cache_data = torch.load(str(CACHE_FILE), map_location="cpu", weights_only=False)
                    self.records = cache_data.get("records", [])
                    self.embeddings = cache_data.get("embeddings", None)
                    self.last_sync_time = cache_data.get("last_sync_time", datetime.now())
                except Exception:
                    pass
            print(f"[INFO] 視覺特徵記憶庫未產生新特徵，維持現有記憶庫 ({len(self.records)} 筆樣本)。")

        # 視覺記憶庫重構完成，同步清空舊有影像診斷快取，保證重新上傳即時生效
        try:
            from app.routers.prediction import clear_image_diagnosis_cache
            clear_image_diagnosis_cache()
        except Exception:
            pass

        return len(self.records)

    def add_or_update(
        self,
        feedback_id: Optional[int] = None,
        image_url: str = "",
        plant_name: str = "",
        disease_name: Optional[str] = None,
        diary_id: Optional[int] = None,
        source: str = "feedback"
    ) -> bool:
        """
        當管理者在後台即時儲存一筆標註（回饋審核或病歷校正）時，
        動態新增或更新記憶庫，內建防污染檢驗，零重啟立即生效！
        """
        # 1. 嚴格防污染檢驗：阻擋 123、測試、純數字等髒資料進入記憶庫
        if not is_valid_crop_name(plant_name):
            print(f"[SECURITY FILTER] 攔截無效作物名稱【{plant_name}】，拒絕刻錄至 Visual Memory。")
            return False

        if disease_name and not is_valid_disease_status(disease_name):
            print(f"[SECURITY FILTER] 攔截無效病害名稱【{disease_name}】，拒絕刻錄至 Visual Memory。")
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

        # 唯一識別碼區分 feedback 或 diary
        if diary_id is not None:
            unique_key = f"diary_{diary_id}"
            eff_feedback_id = -diary_id
        else:
            unique_key = f"feedback_{feedback_id}"
            eff_feedback_id = feedback_id

        # 檢查是否已在 records 內
        existing_idx = None
        for i, r in enumerate(self.records):
            if r.get("unique_key") == unique_key or (source == "feedback" and r.get("feedback_id") == feedback_id):
                existing_idx = i
                break

        if existing_idx is not None:
            self.records[existing_idx]["unique_key"] = unique_key
            self.records[existing_idx]["crop_name"] = plant_name
            self.records[existing_idx]["status_name"] = disease_name or "無法判定"
            self.records[existing_idx]["source"] = source
            if diary_id is not None:
                self.records[existing_idx]["diary_id"] = diary_id
            if emb is not None and self.embeddings is not None:
                self.embeddings[existing_idx] = emb
        elif emb is not None:
            new_record = {
                "unique_key": unique_key,
                "feedback_id": eff_feedback_id,
                "diary_id": diary_id,
                "source": source,
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
        else:
            return False

        self.last_sync_time = datetime.now()
        try:
            torch.save({
                "records": self.records,
                "embeddings": self.embeddings,
                "last_sync_time": self.last_sync_time,
            }, str(CACHE_FILE))
        except Exception as e:
            print(f"[WARN] 即時儲存視覺記憶快取失敗: {e}")

        # 刷新磁碟快取與同步時間
        self.last_sync_time = datetime.now()
        try:
            torch.save({
                "records": self.records,
                "embeddings": self.embeddings,
                "last_sync_time": self.last_sync_time,
            }, str(CACHE_FILE))
        except Exception:
            pass

        # 刻錄新專家記憶後，立即清除舊診斷快取，保證重新上傳同一張時絕不使用舊錯誤輸出
        try:
            from app.routers.prediction import clear_image_diagnosis_cache
            clear_image_diagnosis_cache()
        except Exception:
            pass

        print(f"[VisualMemory] 【{source} #{diary_id or feedback_id}】已成功刻錄至特徵記憶庫：【{plant_name} - {disease_name}】")
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
            sample_ref = f"diary #{matched['diary_id']}" if matched.get("diary_id") else f"feedback #{matched.get('feedback_id')}"
            print(
                f"[VisualMemory 命中] 查詢影像與歷史專家樣本 ({sample_ref}) "
                f"餘弦相似度達 {best_score:.4f} (>= {min_similarity:.2f})！"
                f"成功檢索先驗作物：【{matched['crop_name']}】，歷史病徵：【{matched['status_name']}】"
            )
            return {
                "hit": True,
                "similarity": round(best_score, 4),
                "crop_name": matched["crop_name"],
                "status_name": matched["status_name"],
                "feedback_id": matched.get("feedback_id", 0),
                "diary_id": matched.get("diary_id"),
                "source": matched.get("source", "feedback"),
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
