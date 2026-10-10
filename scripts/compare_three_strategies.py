import argparse
import json
import os
import re
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
from google import genai
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
}

GEMINI_PROMPT = """你是一位專業植物病理學家。請分析這張植物葉片照片，以繁體中文回答以下三個欄位，輸出嚴格合法的 JSON：
{
  "crop_name": "作物名稱 (例如: 番茄, 蘋果, 馬鈴薯, 玉米, 甜椒, 葡萄, 桃, 櫻桃, 大豆, 南瓜, 草莓, 藍莓, 覆盆子，若非植物請填 '未知')",
  "status_name": "病害名稱或狀態 (例如: 早疫病, 晚疫病, 健康, 銹病, 黑星病, 細菌性斑點病, 白粉病，若無病害請填 '健康'，若無法判定填 '無法判定')",
  "confidence": 0.0到1.0之間的信心度浮點數
}
請只回傳 JSON，不要有額外文字或 markdown 程式碼區塊。"""


def parse_gemini_json(text: str) -> dict:
    try:
        clean = re.sub(r"^```json\s*", "", text.strip(), flags=re.MULTILINE)
        clean = re.sub(r"^```\s*", "", clean, flags=re.MULTILINE)
        clean = clean.strip()
        data = json.loads(clean)
        return {
            "crop": str(data.get("crop_name", "")).strip(),
            "status": str(data.get("status_name", "")).strip(),
            "confidence": float(data.get("confidence", 0.8)),
        }
    except Exception:
        return {"crop": "無法解析", "status": "無法解析", "confidence": 0.0}


def run_comparison(data_dir: Path, api_key: str, sample_per_class: int = 1, delay_seconds: float = 4.0):
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    print(f"🚀 硬體加速裝置: {device} ({torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'})")

    # 初始化 ConvNeXt
    conv_model = get_convnext_model()
    if conv_model is None:
        raise RuntimeError("無法載入 ConvNeXt 模型")
    conv_model.to(device)
    conv_model.eval()

    idx_to_class = load_class_index()
    class_to_idx = {v: int(k) for k, v in idx_to_class.items()}

    # 初始化 Gemini Client
    client = genai.Client(api_key=api_key)

    # 挑選測試樣本（按類別抽樣或全選）
    selected_cases = []
    for folder_name, pv_class in PLANTDOC_TO_PLANTVILLAGE.items():
        folder_path = data_dir / folder_name
        if not folder_path.exists():
            continue

        chinese_info = PLANTVILLAGE_TO_CHINESE.get(pv_class, {})
        expected_crop = chinese_info.get("crop", pv_class.split("___")[0])
        expected_status = chinese_info.get("status", pv_class.split("___")[1])
        expected_idx = class_to_idx.get(pv_class)

        # 避免 Windows 大小寫重複 glob
        seen_files = set()
        img_candidates = []
        for ext in ("*.jpg", "*.jpeg", "*.png"):
            for f in folder_path.glob(ext):
                lower_name = f.name.lower()
                if lower_name not in seen_files:
                    seen_files.add(lower_name)
                    img_candidates.append(f)

        if not img_candidates:
            continue

        picked = img_candidates[:sample_per_class] if sample_per_class > 0 else img_candidates
        for img_path in picked:
            selected_cases.append({
                "path": img_path,
                "folder": folder_name,
                "expected_crop": expected_crop,
                "expected_status": expected_status,
                "expected_pv": pv_class,
                "expected_idx": expected_idx,
            })

    total = len(selected_cases)
    print(f"\n🧪 準備進行 3 策略消融實測，共計測試 {total} 張田間樣本...")
    print(f"🕒 每次 Gemini 呼叫間隔等待: {delay_seconds} 秒 (嚴格遵循免費層級 15 RPM 限制)")

    results_table = []
    
    # 統計指標
    stats = {
        "gemini_only": {"correct": 0, "total_time": 0.0, "api_calls": 0},
        "local_only": {"correct": 0, "total_time": 0.0, "api_calls": 0},
        "cascade_strategy": {"correct": 0, "total_time": 0.0, "api_calls": 0, "local_hit": 0, "gemini_fallback": 0},
    }

    for idx, case in enumerate(selected_cases, 1):
        img_path = case["path"]
        exp_crop = case["expected_crop"]
        exp_status = case["expected_status"]
        exp_idx = case["expected_idx"]

        # ==========================================
        # 1. 執行【策略 2：只有本地 ConvNeXt】
        # ==========================================
        t0 = time.perf_counter()
        img_pil = Image.open(img_path).convert("RGB")
        tensor = _transform(img_pil).unsqueeze(0).to(device)
        with torch.no_grad():
            logits = conv_model(tensor)
            probs = torch.softmax(logits, dim=1)
            local_conf, pred_idx = probs.max(dim=1)
            local_conf = local_conf.item()
            pred_idx = pred_idx.item()
        local_latency_ms = (time.perf_counter() - t0) * 1000

        pred_pv_class = idx_to_class[pred_idx]
        pred_chinese = PLANTVILLAGE_TO_CHINESE.get(pred_pv_class, {})
        local_crop = pred_chinese.get("crop", pred_pv_class.split("___")[0])
        local_status = pred_chinese.get("status", pred_pv_class.split("___")[1])
        local_correct = (pred_idx == exp_idx)

        stats["local_only"]["total_time"] += local_latency_ms / 1000
        if local_correct:
            stats["local_only"]["correct"] += 1

        # ==========================================
        # 2. 執行【策略 1：只有 Gemini】
        # ==========================================
        t0 = time.perf_counter()
        try:
            resp = client.models.generate_content(
                model="gemini-3.8-flash",
                contents=[img_pil, GEMINI_PROMPT],
            )
            gemini_data = parse_gemini_json(resp.text)
        except Exception as e:
            gemini_data = {"crop": "API錯誤", "status": str(e)[:15], "confidence": 0.0}
        gemini_latency_s = time.perf_counter() - t0

        gemini_crop = gemini_data["crop"]
        gemini_status = gemini_data["status"]
        # 判斷 Gemini 是否吻合作物與狀態
        gemini_correct = (exp_crop in gemini_crop or gemini_crop in exp_crop) and (
            exp_status in gemini_status or gemini_status in exp_status or (exp_status == "健康" and "健康" in gemini_status)
        )

        stats["gemini_only"]["total_time"] += gemini_latency_s
        stats["gemini_only"]["api_calls"] += 1
        if gemini_correct:
            stats["gemini_only"]["correct"] += 1

        # ==========================================
        # 3. 執行【策略 3：我的級聯雙層策略 (Cascade)】
        # ==========================================
        # 規則：若本地信心度 >= 0.75，直接採信本地；若 < 0.75，則轉交 Gemini 兜底
        cascade_t0 = time.perf_counter()
        if local_conf >= 0.75:
            cascade_choice = "本地快篩 (75ms)"
            cascade_crop = local_crop
            cascade_status = local_status
            cascade_correct = local_correct
            cascade_latency_s = local_latency_ms / 1000
            stats["cascade_strategy"]["local_hit"] += 1
        else:
            cascade_choice = "Gemini兜底 (轉交)"
            cascade_crop = gemini_crop
            cascade_status = gemini_status
            cascade_correct = gemini_correct
            cascade_latency_s = (local_latency_ms / 1000) + gemini_latency_s
            stats["cascade_strategy"]["gemini_fallback"] += 1
            stats["cascade_strategy"]["api_calls"] += 1

        stats["cascade_strategy"]["total_time"] += cascade_latency_s
        if cascade_correct:
            stats["cascade_strategy"]["correct"] += 1

        # 輸出單張日誌
        local_icon = "✅" if local_correct else "❌"
        gemini_icon = "✅" if gemini_correct else "❌"
        cascade_icon = "✅" if cascade_correct else "❌"

        print(f"[{idx:>2}/{total}] 樣本: {case['folder']} | 真實: {exp_crop}-{exp_status}")
        print(f"   ├─ 純本地 : {local_icon} {local_crop}-{local_status} (信心: {local_conf:.2f}, 耗時: {local_latency_ms:.1f}ms)")
        print(f"   ├─ 純雲端 : {gemini_icon} {gemini_crop}-{gemini_status} (耗時: {gemini_latency_s:.2f}s)")
        print(f"   └─ 我的策略: {cascade_icon} 路由: {cascade_choice} -> {cascade_crop}-{cascade_status}")

        results_table.append({
            "image": img_path.name,
            "ground_truth": f"{exp_crop}-{exp_status}",
            "local_result": f"{local_crop}-{local_status}",
            "local_correct": local_correct,
            "local_conf": round(local_conf, 4),
            "gemini_result": f"{gemini_crop}-{gemini_status}",
            "gemini_correct": gemini_correct,
            "cascade_route": cascade_choice,
            "cascade_correct": cascade_correct,
        })

        # 避免 Gemini Free Tier 429 限速
        if idx < total:
            time.sleep(delay_seconds)

    # 彙總報告
    print("\n" + "=" * 70)
    print("🏆 【三種策略消融實驗 (Ablation Study) 實測結果】")
    print("=" * 70)
    print(f"測試樣本總數: {total} 張田間真實照片 (PlantDoc)")
    print("-" * 70)
    print(f"1. 只有本地 (純 ConvNeXt) : 準確率 {(stats['local_only']['correct']/total)*100:5.1f}% | 總耗時 {stats['local_only']['total_time']:5.2f}s | API 消耗 0 次")
    print(f"2. 只有雲端 (純 Gemini)   : 準確率 {(stats['gemini_only']['correct']/total)*100:5.1f}% | 總耗時 {stats['gemini_only']['total_time']:5.2f}s | API 消耗 {stats['gemini_only']['api_calls']} 次")
    print(f"3. 我的策略 (級聯雙層混合): 準確率 {(stats['cascade_strategy']['correct']/total)*100:5.1f}% | 總耗時 {stats['cascade_strategy']['total_time']:5.2f}s | API 消耗 {stats['cascade_strategy']['api_calls']} 次 (節省 {((total - stats['cascade_strategy']['api_calls'])/total)*100:.1f}%)")
    print("=" * 70)

    report = {
        "total_samples": total,
        "local_only": {
            "accuracy": round(stats['local_only']['correct'] / total * 100, 2),
            "total_time_seconds": round(stats['local_only']['total_time'], 2),
            "avg_latency_ms": round((stats['local_only']['total_time'] / total) * 1000, 2),
            "api_calls": 0,
        },
        "gemini_only": {
            "accuracy": round(stats['gemini_only']['correct'] / total * 100, 2),
            "total_time_seconds": round(stats['gemini_only']['total_time'], 2),
            "avg_latency_s": round(stats['gemini_only']['total_time'] / total, 2),
            "api_calls": stats['gemini_only']['api_calls'],
        },
        "cascade_strategy": {
            "accuracy": round(stats['cascade_strategy']['correct'] / total * 100, 2),
            "total_time_seconds": round(stats['cascade_strategy']['total_time'], 2),
            "api_calls": stats['cascade_strategy']['api_calls'],
            "api_saved_percentage": round(((total - stats['cascade_strategy']['api_calls']) / total) * 100, 2),
            "local_hits": stats['cascade_strategy']['local_hit'],
            "gemini_fallbacks": stats['cascade_strategy']['gemini_fallback'],
        },
        "details": results_table,
    }

    report_path = Path("artifacts/three_strategies_ablation_report.json")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\n💾 完整三策略詳細數據已儲存至: {report_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path(r"C:\Users\User\Downloads\PlantDoc-Dataset-master (1)\PlantDoc-Dataset-master\test"),
    )
    parser.add_argument(
        "--api-key",
        type=str,
        default=os.getenv("GEMINI_API_KEY"),
        help="Gemini API Key (預設讀取環境變數 GEMINI_API_KEY)",
    )
    parser.add_argument("--sample-per-class", type=int, default=1, help="每類取幾張 (預設1張=約27張，快速驗證)")
    parser.add_argument("--delay", type=float, default=4.0)
    args = parser.parse_args()

    if not args.api_key:
        raise ValueError("必須提供 --api-key 或設定環境變數 GEMINI_API_KEY")

    run_comparison(args.data_dir, args.api_key, sample_per_class=args.sample_per_class, delay_seconds=args.delay)
