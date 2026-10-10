import argparse
import json
import sys
import time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

import torch
from PIL import Image
from torchvision import transforms

from app.services.convnext import (
    get_convnext_model,
    load_class_index,
    _transform,
    PLANTVILLAGE_TO_CHINESE,
)

PLANTDOC_TO_PLANTVILLAGE = {
    "Apple leaf": "Apple___healthy",
    "Apple rust leaf": "Apple___Cedar_apple_rust",
    "Apple Scab Leaf": "Apple___Apple_scab",
    "Bell_pepper leaf": "Pepper,_bell___healthy",
    "Bell_pepper leaf spot": "Pepper,_bell___Bacterial_spot",
    "Blueberry leaf": "Blueberry___healthy",
    "Cherry leaf": "Cherry_(including_sour)___healthy",
    "Corn Gray leaf spot": "Corn_(maize)___Cercospora_leaf_spot Gray_leaf_spot",
    "Corn leaf blight": "Corn_(maize)___Northern_Leaf_Blight",
    "Corn rust leaf": "Corn_(maize)___Common_rust_",
    "grape leaf": "Grape___healthy",
    "grape leaf black rot": "Grape___Black_rot",
    "Peach leaf": "Peach___healthy",
    "Potato leaf early blight": "Potato___Early_blight",
    "Potato leaf late blight": "Potato___Late_blight",
    "Raspberry leaf": "Raspberry___healthy",
    "Soyabean leaf": "Soybean___healthy",
    "Squash Powdery mildew leaf": "Squash___Powdery_mildew",
    "Strawberry leaf": "Strawberry___healthy",
    "Tomato Early blight leaf": "Tomato___Early_blight",
    "Tomato leaf": "Tomato___healthy",
    "Tomato leaf bacterial spot": "Tomato___Bacterial_spot",
    "Tomato leaf late blight": "Tomato___Late_blight",
    "Tomato leaf mosaic virus": "Tomato___Tomato_mosaic_virus",
    "Tomato leaf yellow virus": "Tomato___Tomato_Yellow_Leaf_Curl_Virus",
    "Tomato mold leaf": "Tomato___Leaf_Mold",
    "Tomato Septoria leaf spot": "Tomato___Septoria_leaf_spot",
    "Tomato two spotted spider mites leaf": "Tomato___Spider_mites Two-spotted_spider_mite",
}


def evaluate_plantdoc(plantdoc_dir: Path, output_file: Path):
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    print(f"🚀 使用硬體加速: {device} ({torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'})")

    model = get_convnext_model()
    if model is None:
        raise RuntimeError("無法載入 ConvNeXt 模型")
    model.to(device)
    model.eval()

    idx_to_class = load_class_index()
    class_to_idx = {v: int(k) for k, v in idx_to_class.items()}

    total_images = 0
    top1_correct = 0
    top3_correct = 0
    crop_correct = 0
    high_conf_count = 0  # 信心度 >= 0.75 (可由 ConvNeXt 獨立結案)
    low_conf_count = 0   # 信心度 < 0.75 (觸發 Gemini 兜底)
    
    crop_stats = {}
    details = []

    start_time = time.perf_counter()

    for folder_name, pv_class in PLANTDOC_TO_PLANTVILLAGE.items():
        folder_path = plantdoc_dir / folder_name
        if not folder_path.exists():
            continue

        expected_idx = class_to_idx.get(pv_class)
        if expected_idx is None:
            continue

        chinese_target = PLANTVILLAGE_TO_CHINESE.get(pv_class, {})
        expected_crop = chinese_target.get("crop", pv_class.split("___")[0])
        expected_status = chinese_target.get("status", pv_class.split("___")[1])

        if expected_crop not in crop_stats:
            crop_stats[expected_crop] = {"total": 0, "top1": 0, "crop_match": 0}

        img_files = list(folder_path.glob("*.jpg")) + list(folder_path.glob("*.JPG")) + list(folder_path.glob("*.png"))
        for img_path in img_files:
            try:
                img = Image.open(img_path).convert("RGB")
                tensor = _transform(img).unsqueeze(0).to(device)

                with torch.no_grad():
                    logits = model(tensor)
                    probs = torch.softmax(logits, dim=1)
                    confidence, pred_idx = probs.max(dim=1)
                    confidence = confidence.item()
                    pred_idx = pred_idx.item()
                    top3_indices = probs.topk(3, dim=1).indices[0].tolist()

                pred_class = idx_to_class[pred_idx]
                pred_chinese = PLANTVILLAGE_TO_CHINESE.get(pred_class, {})
                pred_crop = pred_chinese.get("crop", pred_class.split("___")[0])
                pred_status = pred_chinese.get("status", pred_class.split("___")[1])

                is_top1 = (pred_idx == expected_idx)
                is_top3 = (expected_idx in top3_indices)
                is_crop_match = (pred_crop == expected_crop)

                total_images += 1
                if is_top1:
                    top1_correct += 1
                if is_top3:
                    top3_correct += 1
                if is_crop_match:
                    crop_correct += 1

                crop_stats[expected_crop]["total"] += 1
                if is_top1:
                    crop_stats[expected_crop]["top1"] += 1
                if is_crop_match:
                    crop_stats[expected_crop]["crop_match"] += 1

                if confidence >= 0.75:
                    high_conf_count += 1
                else:
                    low_conf_count += 1

                details.append({
                    "file": img_path.name,
                    "folder": folder_name,
                    "expected": f"{expected_crop}-{expected_status}",
                    "predicted": f"{pred_crop}-{pred_status}",
                    "confidence": round(confidence, 4),
                    "is_top1": is_top1,
                    "is_top3": is_top3,
                    "is_crop_match": is_crop_match,
                })
            except Exception as e:
                print(f"處理失敗 {img_path}: {e}")

    elapsed = time.perf_counter() - start_time
    avg_latency = (elapsed / total_images) * 1000 if total_images else 0

    top1_rate = (top1_correct / total_images * 100) if total_images else 0
    top3_rate = (top3_correct / total_images * 100) if total_images else 0
    crop_rate = (crop_correct / total_images * 100) if total_images else 0

    print("\n" + "=" * 65)
    print("🌾 【PlantDoc 真實農田（跨域野外環境）實測報告】")
    print("=" * 65)
    print(f"測試集來源       : PlantDoc (真實田間 / 非實驗室純色背景)")
    print(f"測試樣本數       : {total_images} 張真實農地照片")
    print(f"總耗時           : {elapsed:.2f} 秒 (平均每張 {avg_latency:.2f} ms)")
    print("-" * 65)
    print(f"1. 作物識別準確率 : {crop_rate:.2f}% ({crop_correct}/{total_images})")
    print(f"2. Top-1 病害準確率: {top1_rate:.2f}% ({top1_correct}/{total_images})")
    print(f"3. Top-3 病害準確率: {top3_rate:.2f}% ({top3_correct}/{total_images})")
    print("-" * 65)
    print(f"💡 【系統級聯決策分析（亮點證明）】:")
    print(f"  • 高信心命中 (>= 75% 邊緣直接判定) : {high_conf_count} 張 ({high_conf_count/total_images*100:.1f}%)")
    print(f"  • 觸發 Gemini 兜底接手 (< 75% 降級) : {low_conf_count} 張 ({low_conf_count/total_images*100:.1f}%)")
    print("=" * 65)

    print("\n📊 【各作物在真實田間之識別表現】:")
    for crop, stat in sorted(crop_stats.items()):
        acc = (stat["top1"] / stat["total"] * 100) if stat["total"] else 0
        c_acc = (stat["crop_match"] / stat["total"] * 100) if stat["total"] else 0
        print(f"  - {crop:<6} : 作物命中率 {c_acc:5.1f}% | 病害命中率 {acc:5.1f}% ({stat['top1']}/{stat['total']} 張)")

    report = {
        "dataset": "PlantDoc (In-the-wild)",
        "total_images": total_images,
        "crop_accuracy": round(crop_rate, 2),
        "top1_accuracy": round(top1_rate, 2),
        "top3_accuracy": round(top3_rate, 2),
        "high_confidence_direct_hits": high_conf_count,
        "fallback_to_gemini_triggered": low_conf_count,
        "crop_breakdown": crop_stats,
    }

    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\n💾 報告已儲存至: {output_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path(r"C:\Users\User\Downloads\PlantDoc-Dataset-master (1)\PlantDoc-Dataset-master\test"),
        help="PlantDoc test directory",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/plantdoc_eval_report.json"),
    )
    args = parser.parse_args()
    evaluate_plantdoc(args.data_dir, args.output)
