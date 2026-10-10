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

from dotenv import load_dotenv
load_dotenv(ROOT_DIR / ".env")

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

import timm
import torch
from PIL import Image
from google import genai
from torchvision import transforms

from app.services.convnext import (
    load_class_index,
    _transform,
    PLANTVILLAGE_TO_CHINESE,
)
from scripts.evaluate_ai_challenger import AIC_TO_PV

# 繁簡與別名同義詞映射表 (讓 AI Challenger 與 Gemini 回傳的中文完全公平判定)
SYNONYMS = {
    "甜椒": ["甜椒", "辣椒", "椒"],
    "辣椒": ["甜椒", "辣椒", "椒"],
    "柑橘": ["柑橘", "柑桔", "橘", "桔", "橙"],
    "馬鈴薯": ["馬鈴薯", "土豆", "洋芋"],
    "番茄": ["番茄", "西紅柿"],
    "桃": ["桃", "桃子"],
    "櫻桃": ["櫻桃", "車厘子"],
    # 病害同義詞
    "細菌性穿孔病": ["細菌性穿孔病", "穿孔病", "瘡痂病", "穿孔", "細菌性"],
    "細菌性斑點病": ["細菌性斑點病", "斑點病", "瘡痂病", "細菌性"],
    "葉焦病": ["葉焦病", "葉枯病", "枯病", "焦枯病"],
    "花葉病毒病": ["花葉病毒病", "嵌紋病毒病", "花葉病", "嵌紋病", "花葉"],
    "嵌紋病毒病": ["花葉病毒病", "嵌紋病毒病", "花葉病", "嵌紋病", "花葉"],
    "黃化捲葉病毒病": ["黃化捲葉病毒病", "黃化曲葉病毒病", "黃化捲葉", "黃化曲葉", "曲葉病", "捲葉病"],
    "二點葉蟎": ["二點葉蟎", "紅蜘蛛", "葉蟎", "蜘蛛", "蟎害"],
    "靶斑病": ["靶斑病", "斑點病", "靶斑"],
    "黑星病": ["黑星病", "瘡痂病"],
}

GEMINI_PROMPT = """你是一位專業植物病理學家。請分析這張植物葉片照片，以繁體中文回答以下三個欄位，輸出嚴格合法的 JSON：
{
  "crop_name": "作物名稱 (例如: 番茄, 蘋果, 馬鈴薯, 玉米, 甜椒, 葡萄, 桃, 櫻桃, 大豆, 南瓜, 草莓, 柑橘，若非植物請填 '未知')",
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


def is_match(expected: str, predicted: str, synonyms_dict: dict) -> bool:
    if expected in predicted or predicted in expected:
        return True
    expected_syns = synonyms_dict.get(expected, [expected])
    predicted_syns = synonyms_dict.get(predicted, [predicted])
    for s1 in expected_syns:
        for s2 in predicted_syns:
            if s1 in predicted or s2 in expected or s1 == s2:
                return True
    return False


def run_ai_challenger_comparison(val_dir: Path, api_key: str, sample_per_class: int = 1, delay_seconds: float = 4.2):
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    print(f"🚀 硬體加速裝置: {device} ({torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'})")

    idx_to_class = load_class_index()
    class_to_idx = {v: int(k) for k, v in idx_to_class.items()}
    num_classes = len(idx_to_class)

    # 載入當前最佳微調 ConvNeXt 模型
    conv_model = timm.create_model("convnext_small", num_classes=num_classes, pretrained=False)
    conv_model.load_state_dict(torch.load("convnext_plant_best.pth", map_location="cpu"))
    conv_model.to(device)
    conv_model.eval()

    # 初始化 Gemini
    client = genai.Client(api_key=api_key)

    # 挑選樣本
    selected_cases = []
    seen_files = set()
    for folder_str in sorted(AIC_TO_PV.keys(), key=lambda x: int(x)):
        folder_path = val_dir / folder_str
        if not folder_path.exists():
            continue
        pv_class = AIC_TO_PV[folder_str]
        chinese_info = PLANTVILLAGE_TO_CHINESE.get(pv_class, {})
        exp_crop = chinese_info.get("crop", pv_class.split("___")[0])
        exp_status = chinese_info.get("status", pv_class.split("___")[1])
        exp_idx = class_to_idx.get(pv_class)

        img_candidates = []
        for ext in ("*.jpg", "*.jpeg", "*.png"):
            for f in folder_path.glob(ext):
                lower = f.name.lower()
                if lower not in seen_files:
                    seen_files.add(lower)
                    img_candidates.append(f)

        if not img_candidates:
            continue

        picked = img_candidates[:sample_per_class] if sample_per_class > 0 else img_candidates
        for img_path in picked:
            selected_cases.append({
                "path": img_path,
                "folder": folder_str,
                "expected_crop": exp_crop,
                "expected_status": exp_status,
                "expected_pv": pv_class,
                "expected_idx": exp_idx,
            })

    total = len(selected_cases)
    print(f"\n🧪 準備進行 AI Challenger 跨領域 3 策略實測，涵蓋 {len(AIC_TO_PV)} 種病害，共計 {total} 張樣本...")
    print(f"🕒 每次 Gemini 呼叫間隔等待: {delay_seconds} 秒 (嚴格遵循免費層級 15 RPM 限制)")

    results_table = []
    stats = {
        "gemini_only": {"correct": 0, "total_time": 0.0, "api_calls": 0},
        "local_only": {"correct": 0, "total_time": 0.0, "api_calls": 0},
        "cascade_strategy": {"correct": 0, "total_time": 0.0, "api_calls": 0, "local_hit": 0, "gemini_fallback": 0},
    }

    # Checkpoint 載入
    ckpt_path = Path("artifacts/ai_challenger_three_strategies_checkpoint.json")
    processed_images = set()
    if ckpt_path.exists():
        try:
            with open(ckpt_path, "r", encoding="utf-8") as ckpt_f:
                saved = json.load(ckpt_f)
                if saved.get("total") == total:
                    results_table = saved.get("details", [])
                    stats = saved.get("stats", stats)
                    processed_images = {r["image"] for r in results_table}
                    print(f"🔄 偵測到已有斷點記錄，成功接續 {len(results_table)} 張已測試樣本！")
        except Exception:
            pass

    for idx, case in enumerate(selected_cases, 1):
        img_path = case["path"]
        if img_path.name in processed_images:
            continue

        exp_crop = case["expected_crop"]
        exp_status = case["expected_status"]
        exp_idx = case["expected_idx"]

        # 1. 策略 2：純本地 ConvNeXt
        t0 = time.perf_counter()
        img_pil = Image.open(img_path).convert("RGB")
        tensor = _transform(img_pil).unsqueeze(0).to(device)
        with torch.no_grad():
            outputs = conv_model(tensor)
            probs = torch.softmax(outputs, dim=1)
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

        # 2. 策略 1：純 Gemini 3.8 Flash (公平性保障：持續重試直到回傳)
        gemini_data = None
        gemini_latency_s = 0.0
        attempt = 0
        while gemini_data is None:
            attempt += 1
            t_call = time.perf_counter()
            try:
                resp = client.models.generate_content(
                    model="gemini-3.8-flash",
                    contents=[img_pil, GEMINI_PROMPT],
                )
                gemini_latency_s = time.perf_counter() - t_call
                gemini_data = parse_gemini_json(resp.text)
                if gemini_data.get("crop") == "無法解析":
                    if attempt < 3:
                        time.sleep(2)
                        gemini_data = None
                        continue
            except Exception as e:
                err_str = str(e)
                if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str or "Quota" in err_str:
                    print(f"      ⏳ [429 Quota Exceeded] 觸發免費頻率限制，等待 20 秒重試 (第 {attempt} 次)...")
                    time.sleep(20)
                elif "503" in err_str or "UNAVAILABLE" in err_str:
                    print(f"      ⏳ [503 Service Unavailable] Google 忙碌，等待 6 秒重試 (第 {attempt} 次)...")
                    time.sleep(6)
                else:
                    print(f"      ⏳ [連線異常] 等待 4 秒重試 (第 {attempt} 次)...")
                    time.sleep(4)

        gemini_crop = gemini_data["crop"]
        gemini_status = gemini_data["status"]

        gemini_crop_correct = is_match(exp_crop, gemini_crop, SYNONYMS)
        gemini_status_correct = is_match(exp_status, gemini_status, SYNONYMS)
        gemini_correct = gemini_crop_correct and gemini_status_correct

        stats["gemini_only"]["total_time"] += gemini_latency_s
        stats["gemini_only"]["api_calls"] += 1
        if gemini_correct:
            stats["gemini_only"]["correct"] += 1

        # 3. 策略 3：階層式級聯策略 (Cascade: 門檻 0.70)
        cascade_t0 = time.perf_counter()
        if local_conf >= 0.70:
            cascade_choice = "本地快篩 (66ms)"
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

        local_icon = "✅" if local_correct else "❌"
        gemini_icon = "✅" if gemini_correct else "❌"
        cascade_icon = "✅" if cascade_correct else "❌"

        print(f"[{idx:>2}/{total}] 類別 {case['folder']:>2} | 真實: {exp_crop}-{exp_status}")
        print(f"   ├─ 純本地 : {local_icon} {local_crop}-{local_status} (信心: {local_conf:.2f}, 耗時: {local_latency_ms:.1f}ms)")
        print(f"   ├─ 純雲端 : {gemini_icon} {gemini_crop}-{gemini_status} (耗時: {gemini_latency_s:.2f}s)")
        print(f"   └─ 我的策略: {cascade_icon} 路由: {cascade_choice} -> {cascade_crop}-{cascade_status}")

        results_table.append({
            "image": img_path.name,
            "category_id": case["folder"],
            "ground_truth": f"{exp_crop}-{exp_status}",
            "local_result": f"{local_crop}-{local_status}",
            "local_correct": local_correct,
            "local_conf": round(local_conf, 4),
            "gemini_result": f"{gemini_crop}-{gemini_status}",
            "gemini_correct": gemini_correct,
            "cascade_route": cascade_choice,
            "cascade_correct": cascade_correct,
        })

        # Checkpoint 保存
        ckpt_path.parent.mkdir(parents=True, exist_ok=True)
        with open(ckpt_path, "w", encoding="utf-8") as ckpt_f:
            json.dump({
                "processed": len(results_table),
                "total": total,
                "stats": stats,
                "details": results_table,
            }, ckpt_f, ensure_ascii=False, indent=2)

        if idx < total:
            time.sleep(delay_seconds)

    # 結算報告
    print("\n" + "=" * 70)
    print("🏆 【AI Challenger 跨資料集三策略消融評測結果】")
    print("=" * 70)
    print(f"測試樣本總數: {total} 張完全第三方實拍樣本 (涵蓋 {len(AIC_TO_PV)} 種病害)")
    print("-" * 70)
    print(f"1. 只有本地 (純 ConvNeXt) : 準確率 {(stats['local_only']['correct']/total)*100:5.1f}% | 總耗時 {stats['local_only']['total_time']:5.2f}s | API 消耗 0 次")
    print(f"2. 只有雲端 (純 Gemini 3.8): 準確率 {(stats['gemini_only']['correct']/total)*100:5.1f}% | 總耗時 {stats['gemini_only']['total_time']:5.2f}s | API 消耗 {stats['gemini_only']['api_calls']} 次")
    print(f"3. 我的策略 (級聯雙層混合): 準確率 {(stats['cascade_strategy']['correct']/total)*100:5.1f}% | 總耗時 {stats['cascade_strategy']['total_time']:5.2f}s | API 消耗 {stats['cascade_strategy']['api_calls']} 次 (節省 {((total - stats['cascade_strategy']['api_calls'])/total)*100:.1f}%)")
    print("=" * 70)

    report = {
        "total_samples": total,
        "local_only": {
            "accuracy": round(stats['local_only']['correct'] / total * 100, 2),
            "total_time_seconds": round(stats['local_only']['total_time'], 2),
            "api_calls": 0,
        },
        "gemini_only": {
            "accuracy": round(stats['gemini_only']['correct'] / total * 100, 2),
            "total_time_seconds": round(stats['gemini_only']['total_time'], 2),
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

    report_path = Path("artifacts/ai_challenger_three_strategies_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\n💾 評測報表已儲存至: {report_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--val-dir", type=Path, default=Path(r"C:\Users\User\Downloads\val"))
    parser.add_argument("--api-key", type=str, default=os.getenv("GEMINI_API_KEY"))
    parser.add_argument("--sample-per-class", type=int, default=1, help="每類抽取幾張 (預設1張=55張，涵蓋全病害)")
    parser.add_argument("--delay", type=float, default=4.2)
    args = parser.parse_args()

    if not args.api_key:
        raise ValueError("必須提供 --api-key 或設定環境變數 GEMINI_API_KEY")

    run_ai_challenger_comparison(args.val_dir, args.api_key, sample_per_class=args.sample_per_class, delay_seconds=args.delay)

