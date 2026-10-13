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

EXPORT_DIR = settings.BASE_DIR / "dataset" / "feedback_training"
UNKNOWN_SET = {"未知", "未知作物", "無法判定", "無法辨識", "非植物", "無植物特徵"}


def export_feedback_dataset(output_dir: Path = EXPORT_DIR) -> Dict[str, Any]:
    """
    從 MySQL diagnosis_feedback 匯出具備專家/管理者校正的田間影像，
    組織成標準 PyTorch ImageFolder 資料夾結構：
    dataset/feedback_training/<作物___病徵>/<影像檔名>.jpg
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    conn = get_db_connection()
    rows = []
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
            rows = cursor.fetchall()
    finally:
        conn.close()

    exported_count = 0
    class_stats = {}
    details = []

    for r in rows:
        crop = (r.get("manager_corrected_plant_name") or r.get("corrected_plant_name") or "").strip()
        disease = (r.get("manager_corrected_disease_name") or r.get("corrected_disease_name") or r.get("original_disease_name") or "健康").strip()

        if not crop or crop in UNKNOWN_SET or disease in UNKNOWN_SET:
            continue

        rel_img = r.get("image_url", "")
        src_path = settings.BASE_DIR / rel_img
        if not src_path.exists():
            continue

        # 規範化類別名稱：作物___病害
        class_folder_name = f"{crop}___{disease}".replace(" ", "_").replace("/", "_")
        target_folder = output_dir / class_folder_name
        target_folder.mkdir(parents=True, exist_ok=True)

        target_file_name = f"feedback_{r['id']}_{src_path.name}"
        target_path = target_folder / target_file_name

        shutil.copy2(str(src_path), str(target_path))
        exported_count += 1
        class_stats[class_folder_name] = class_stats.get(class_folder_name, 0) + 1

        details.append({
            "feedback_id": r["id"],
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
