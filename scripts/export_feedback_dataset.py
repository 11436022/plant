import os
import sys
import shutil
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

# 確保專案根目錄在 sys.path 中
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import settings
from app.db.session import get_db_connection
from app.services.visual_memory import is_valid_crop_name, is_valid_disease_status

EXPORT_DIR = settings.BASE_DIR / "dataset" / "feedback_training"
UNKNOWN_SET = {"未知", "未知作物", "無法判定", "無法辨識", "非植物", "無植物特徵"}


def export_feedback_dataset(output_dir: Path = EXPORT_DIR) -> Dict[str, Any]:
    """
    從 MySQL diagnosis_feedback 與 plant_diary 匯出具備專家/管理者校正的田間影像，
    經防污染清洗後，組織成標準 PyTorch ImageFolder 資料夾結構：
    dataset/feedback_training/<作物___病徵>/<影像檔名>.jpg
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    conn = get_db_connection()
    feedback_rows = []
    diary_rows = []
    try:
        import pymysql
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            # 1. 讀取 diagnosis_feedback (UC-14)
            sql_fb = """
                SELECT id, image_url, original_plant_name, original_disease_name,
                       corrected_plant_name, corrected_disease_name,
                       manager_corrected_plant_name, manager_corrected_disease_name,
                       created_at
                FROM diagnosis_feedback
                WHERE (manager_corrected_plant_name IS NOT NULL AND manager_corrected_plant_name != '')
                   OR (corrected_plant_name IS NOT NULL AND corrected_plant_name != '')
                ORDER BY id ASC
            """
            cursor.execute(sql_fb)
            feedback_rows = cursor.fetchall()

            # 2. 讀取 plant_diary 專家校正 (UC-08)
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
    finally:
        conn.close()

    exported_count = 0
    class_stats = {}
    details = []

    # 匯出 feedback 樣本
    for r in feedback_rows:
        crop = (r.get("manager_corrected_plant_name") or r.get("corrected_plant_name") or "").strip()
        disease = (r.get("manager_corrected_disease_name") or r.get("corrected_disease_name") or r.get("original_disease_name") or "健康").strip()

        # 嚴格防污染清洗：非合法作物或病名（如 123、測試、純數字等）直接過濾，嚴防污染訓練集
        if not is_valid_crop_name(crop) or not is_valid_disease_status(disease):
            print(f"[SECURITY FILTER] 匯出過濾回饋 #{r['id']} 髒資料標籤：【{crop} - {disease}】")
            continue

        rel_img = r.get("image_url", "")
        clean_rel = str(rel_img).replace("\\", "/")
        if "static/" in clean_rel:
            clean_rel = "static/" + clean_rel.split("static/", 1)[1]
        else:
            clean_rel = clean_rel.lstrip("/")
        src_path = settings.BASE_DIR / clean_rel
        if not src_path.exists():
            continue

        class_folder_name = f"{crop}___{disease}".replace(" ", "_").replace("/", "_")
        target_folder = output_dir / class_folder_name
        target_folder.mkdir(parents=True, exist_ok=True)

        target_file_name = f"feedback_{r['id']}_{src_path.name}"
        target_path = target_folder / target_file_name

        shutil.copy2(str(src_path), str(target_path))
        exported_count += 1
        class_stats[class_folder_name] = class_stats.get(class_folder_name, 0) + 1

        details.append({
            "source": "feedback",
            "source_id": r["id"],
            "crop": crop,
            "disease": disease,
            "class_folder": class_folder_name,
            "filename": target_file_name,
            "exported_at": datetime.now().isoformat(),
        })

    # 匯出 diary 專家校正樣本
    for r in diary_rows:
        crop = (r.get("crop_name") or "").strip()
        disease = (r.get("user_corrected_status") or "").strip()

        if not crop and disease:
            for kw, cp in [
                ("柑橘", "柑橘"), ("番茄", "番茄"), ("馬鈴薯", "馬鈴薯"),
                ("蘋果", "蘋果"), ("玉米", "玉米"), ("葡萄", "葡萄"),
                ("草莓", "草莓"), ("甜椒", "甜椒")
            ]:
                if kw in disease or kw in (r.get("status_name") or ""):
                    crop = cp
                    break

        if not is_valid_crop_name(crop) or not is_valid_disease_status(disease):
            print(f"[SECURITY FILTER] 匯出過濾日記 #{r['id']} 髒資料標籤：【{crop} - {disease}】")
            continue

        rel_img = r.get("image_url", "")
        clean_rel = str(rel_img).replace("\\", "/")
        if "static/" in clean_rel:
            clean_rel = "static/" + clean_rel.split("static/", 1)[1]
        else:
            clean_rel = clean_rel.lstrip("/")
        src_path = settings.BASE_DIR / clean_rel
        if not src_path.exists():
            continue

        class_folder_name = f"{crop}___{disease}".replace(" ", "_").replace("/", "_")
        target_folder = output_dir / class_folder_name
        target_folder.mkdir(parents=True, exist_ok=True)

        target_file_name = f"diary_{r['id']}_{src_path.name}"
        target_path = target_folder / target_file_name

        shutil.copy2(str(src_path), str(target_path))
        exported_count += 1
        class_stats[class_folder_name] = class_stats.get(class_folder_name, 0) + 1

        details.append({
            "source": "diary",
            "source_id": r["id"],
            "crop": crop,
            "disease": disease,
            "class_folder": class_folder_name,
            "filename": target_file_name,
            "exported_at": datetime.now().isoformat(),
        })

    manifest = {
        "export_time": datetime.now().isoformat(),
        "total_images": exported_count,
        "class_count": len(class_stats),
        "class_breakdown": class_stats,
        "details": details,
    }

    manifest_path = output_dir / "dataset_manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    print(f"[OK] 成功導出 {exported_count} 張田間標註影像至 {output_dir} (共 {len(class_stats)} 個類別)")
    return manifest


if __name__ == "__main__":
    export_feedback_dataset()
