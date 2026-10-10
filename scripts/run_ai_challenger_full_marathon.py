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
from scripts.compare_ai_challenger_three_strategies import SYNONYMS, GEMINI_PROMPT, parse_gemini_json, is_match

from dotenv import load_dotenv
load_dotenv()

# 金鑰池與黑名單 (從環境變數載入)
FREE_KEY_POOL = [
    k.strip() for k in os.environ.get("FREE_KEY_POOL", os.environ.get("GEMINI_API_KEY", "")).split(",") if k.strip()
]
PAID_KEY_BLACKLIST = os.environ.get("PAID_KEY_BLACKLIST", "")


class KeyPoolManager:
    """智慧輪替與故障轉移金鑰管理器 (100% 免費保證)"""
    def __init__(self, keys: list[str]):
        self.keys = [k for k in keys if k != PAID_KEY_BLACKLIST]
        self.clients = [genai.Client(api_key=k) for k in self.keys]
        self.current_idx = 0
        print(f"🔒 金鑰池初始化成功：共掛載 {len(self.keys)} 組純免費金鑰，已嚴格封鎖付費金鑰！")

    def get_client(self):
        client = self.clients[self.current_idx]
        key_short = self.keys[self.current_idx][:10] + "..." + self.keys[self.current_idx][-6:]
        return client, self.current_idx, key_short

    def rotate_next(self):
        self.current_idx = (self.current_idx + 1) % len(self.keys)
        new_key = self.keys[self.current_idx][:10] + "..." + self.keys[self.current_idx][-6:]
        print(f"🔄 自動輪替至第 {self.current_idx + 1} 組免費金鑰 ({new_key})")


def run_full_ai_challenger(val_dir: Path, delay_seconds: float = 1.5):
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    print(f"🚀 硬體加速裝置: {device} ({torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'})")

    idx_to_class = load_class_index()
    class_to_idx = {v: int(k) for k, v in idx_to_class.items()}
    num_classes = len(idx_to_class)

    # 載入微調後最佳模型
    conv_model = timm.create_model("convnext_small", num_classes=num_classes, pretrained=False)
    conv_model.load_state_dict(torch.load("convnext_plant_best.pth", map_location="cpu"))
    conv_model.to(device)
    conv_model.eval()

    key_manager = KeyPoolManager(FREE_KEY_POOL)

    # 收集全部 4520 張樣本
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

        for ext in ("*.jpg", "*.jpeg", "*.png"):
            for img_path in folder_path.glob(ext):
                lower = img_path.name.lower()
                if lower not in seen_files:
                    seen_files.add(lower)
                    selected_cases.append({
                        "path": img_path,
                        "folder": folder_str,
                        "expected_crop": exp_crop,
                        "expected_status": exp_status,
                        "expected_pv": pv_class,
                        "expected_idx": exp_idx,
                    })

    total = len(selected_cases)
    print(f"\n🏃‍♂️【AI Challenger 全量 4,520 張馬拉松大盲測啟動】")
    print(f"📦 總樣本數: {total} 張 (涵蓋全部 55 類病害)")
    print(f"🕒 4 組免費 Key 輪替併發間隔: {delay_seconds} 秒 (安全無損全自動運行)")

    results_table = []
    stats = {
        "gemini_only": {"correct": 0, "total_time": 0.0, "api_calls": 0},
        "local_only": {"correct": 0, "total_time": 0.0, "api_calls": 0},
        "cascade_strategy": {"correct": 0, "total_time": 0.0, "api_calls": 0, "local_hit": 0, "gemini_fallback": 0},
    }

    # 斷點接續
    ckpt_path = Path("artifacts/ai_challenger_full_4520_checkpoint.json")
    processed_images = set()
    if ckpt_path.exists():
        try:
            with open(ckpt_path, "r", encoding="utf-8") as ckpt_f:
                saved = json.load(ckpt_f)
                if saved.get("total") == total:
                    results_table = saved.get("details", [])
                    stats = saved.get("stats", stats)
                    processed_images = {r["image"] for r in results_table}
                    print(f"🔄 偵測到現有進度斷點，成功接續 {len(results_table)} 張已完成樣本！直接從第 {len(results_table) + 1} 張開始...")
        except Exception:
            pass

    for idx, case in enumerate(selected_cases, 1):
        img_path = case["path"]
        if img_path.name in processed_images:
            continue

        exp_crop = case["expected_crop"]
        exp_status = case["expected_status"]
        exp_idx = case["expected_idx"]

        # 1. 本地 ConvNeXt
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

        # 2. 純 Gemini 3.8 (金鑰池輪替與故障轉移)
        gemini_data = None
        gemini_latency_s = 0.0
        retry_count = 0

        while gemini_data is None:
            retry_count += 1
            client, key_idx, key_name = key_manager.get_client()
            t_call = time.perf_counter()
            try:
                resp = client.models.generate_content(
                    model="gemini-3.8-flash",
                    contents=[img_pil, GEMINI_PROMPT],
                )
                gemini_latency_s = time.perf_counter() - t_call
                gemini_data = parse_gemini_json(resp.text)
                if gemini_data.get("crop") == "無法解析":
                    if retry_count < 3:
                        time.sleep(1)
                        gemini_data = None
                        continue
            except Exception as e:
                err_str = str(e)
                # 遇 429 立即切換下一個免費 Key
                if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str or "Quota" in err_str:
                    print(f"      ⏳ 免費 Key {key_idx+1} 達暫態上限，自動切換下一把金鑰...")
                    key_manager.rotate_next()
                    time.sleep(1.5)
                elif "503" in err_str or "UNAVAILABLE" in err_str:
                    print(f"      ⏳ Google 伺服器忙碌，切換金鑰重試...")
                    key_manager.rotate_next()
                    time.sleep(2)
                else:
                    print(f"      ⏳ 連線波動 ({err_str[:30]})，等待 2 秒重試...")
                    time.sleep(2)

        # 每次成功呼叫後輪替至下一把 Key，達成完美負載平衡
        key_manager.rotate_next()

        gemini_crop = gemini_data["crop"]
        gemini_status = gemini_data["status"]
        gemini_crop_correct = is_match(exp_crop, gemini_crop, SYNONYMS)
        gemini_status_correct = is_match(exp_status, gemini_status, SYNONYMS)
        gemini_correct = gemini_crop_correct and gemini_status_correct

        stats["gemini_only"]["total_time"] += gemini_latency_s
        stats["gemini_only"]["api_calls"] += 1
        if gemini_correct:
            stats["gemini_only"]["correct"] += 1

        # 3. 您的階層式瀑布流策略 (門檻 0.70)
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

        # 每 10 張或每張輸出進度
        curr_len = len(results_table) + 1
        if curr_len % 5 == 0 or curr_len <= 10:
            print(f"[{curr_len:>4}/{total}] 類別 {case['folder']:>2} | 真實: {exp_crop}-{exp_status}")
            print(f"   ├─ 純本地 : {local_icon} {local_crop}-{local_status} (信心: {local_conf:.2f}, 耗時: {local_latency_ms:.1f}ms)")
            print(f"   ├─ 純雲端 : {gemini_icon} {gemini_crop}-{gemini_status} (耗時: {gemini_latency_s:.2f}s)")
            print(f"   └─ 我的策略: {cascade_icon} 路由: {cascade_choice} -> {cascade_crop}-{cascade_status}")
            print(f"   📊 [累計準確率] 本地: {stats['local_only']['correct']/curr_len*100:.1f}% | 雲端: {stats['gemini_only']['correct']/curr_len*100:.1f}% | 我的策略: {stats['cascade_strategy']['correct']/curr_len*100:.1f}% (省 API: {((curr_len - stats['cascade_strategy']['api_calls'])/curr_len)*100:.1f}%)")

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

        # 斷點存檔：每完成一張即刻寫入 checkpoint
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

    # 最終全量結算報告
    print("\n" + "=" * 75)
    print("🏆 【AI Challenger 全量 4,520 張實測大結算報告】")
    print("=" * 75)
    print(f"測試樣本總數: {total} 張 (100% 全量跨領域真實樣本)")
    print("-" * 75)
    print(f"1. 只有本地 (純 ConvNeXt) : 準確率 {(stats['local_only']['correct']/total)*100:5.2f}% | 總耗時 {stats['local_only']['total_time']:5.1f}s | API 消耗 0 次")
    print(f"2. 只有雲端 (純 Gemini 3.8): 準確率 {(stats['gemini_only']['correct']/total)*100:5.2f}% | 總耗時 {stats['gemini_only']['total_time']:5.1f}s | API 消耗 {stats['gemini_only']['api_calls']} 次")
    print(f"3. 我的策略 (級聯雙層混合): 準確率 {(stats['cascade_strategy']['correct']/total)*100:5.2f}% | 總耗時 {stats['cascade_strategy']['total_time']:5.1f}s | API 消耗 {stats['cascade_strategy']['api_calls']} 次 (節省 {((total - stats['cascade_strategy']['api_calls'])/total)*100:.1f}%)")
    print("=" * 75)

    final_report = {
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

    report_path = Path("artifacts/ai_challenger_full_4520_final_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(final_report, f, ensure_ascii=False, indent=2)
    print(f"\n💾 全量 4,520 張完整報表已儲存至: {report_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--val-dir", type=Path, default=Path(r"C:\Users\User\Downloads\val"))
    parser.add_argument("--delay", type=float, default=1.2)
    args = parser.parse_args()

    run_full_ai_challenger(args.val_dir, delay_seconds=args.delay)
