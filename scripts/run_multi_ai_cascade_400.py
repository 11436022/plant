import argparse
import base64
import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import functools
print = functools.partial(print, flush=True)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

import timm
import torch
from PIL import Image
from torchvision import transforms

from app.services.convnext import load_class_index, _transform, PLANTVILLAGE_TO_CHINESE
from scripts.evaluate_ai_challenger import AIC_TO_PV
from scripts.compare_ai_challenger_three_strategies import SYNONYMS, is_match

# 雲端 AI 模組
from google import genai
from openai import OpenAI
from anthropic import Anthropic

from dotenv import load_dotenv
load_dotenv()

# API Keys (從 .env 安全載入，嚴禁硬編碼上傳)
GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "")
OPENAI_KEY = os.environ.get("OPENAI_API_KEY", "")
ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

PROMPT_TEXT = (
    "你是一位頂尖的農業病理學家與植物保護專家。請仔細觀察這張照片中的葉片，辨識其作物種類與健康狀態/病害名稱。\n"
    "請嚴格以繁體中文 JSON 格式回答，不要有任何多餘贅字或 markdown 包裹以外的文字：\n"
    '{"crop": "作物名稱", "status": "病害名稱或健康"}\n'
    "範例：\n"
    '{"crop": "番茄", "status": "早疫病"}\n'
    '{"crop": "玉米", "status": "健康"}'
)

def parse_llm_json(raw_text: str) -> dict:
    if not raw_text:
        return {"crop": "無法解析", "status": "無法解析"}
    m = re.search(r"\{.*?\}", raw_text, re.DOTALL)
    if m:
        try:
            d = json.loads(m.group(0))
            return {
                "crop": str(d.get("crop", "無法解析")).strip(),
                "status": str(d.get("status", "無法解析")).strip()
            }
        except Exception:
            pass
    return {"crop": "無法解析", "status": "無法解析"}

# 初始化各 API Client
gemini_client = genai.Client(api_key=GEMINI_KEY)
openai_client = OpenAI(api_key=OPENAI_KEY)
anthropic_client = Anthropic(api_key=ANTHROPIC_KEY)

def query_gemini(img_pil: Image.Image) -> tuple[dict, float]:
    t0 = time.perf_counter()
    for attempt in range(3):
        try:
            resp = gemini_client.models.generate_content(
                model="gemini-3.8-flash",
                contents=[img_pil, PROMPT_TEXT],
            )
            lat = time.perf_counter() - t0
            return parse_llm_json(resp.text), lat
        except Exception as e:
            time.sleep(1.5 * (attempt + 1))
    return {"crop": "錯誤", "status": "錯誤"}, time.perf_counter() - t0

def query_openai(b64_img: str) -> tuple[dict, float]:
    t0 = time.perf_counter()
    for attempt in range(3):
        try:
            resp = openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": PROMPT_TEXT},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_img}", "detail": "high"}}
                        ]
                    }
                ],
                response_format={"type": "json_object"},
                max_tokens=150
            )
            lat = time.perf_counter() - t0
            return parse_llm_json(resp.choices[0].message.content), lat
        except Exception as e:
            time.sleep(1.5 * (attempt + 1))
    return {"crop": "錯誤", "status": "錯誤"}, time.perf_counter() - t0

def query_claude(b64_img: str) -> tuple[dict, float]:
    t0 = time.perf_counter()
    for attempt in range(3):
        try:
            resp = anthropic_client.messages.create(
                model="claude-sonnet-5",
                max_tokens=300,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": b64_img}},
                            {"type": "text", "text": PROMPT_TEXT}
                        ]
                    }
                ]
            )
            # 遍歷 content 提取文字
            raw_text = ""
            for block in resp.content:
                if hasattr(block, "text"):
                    raw_text += block.text
            lat = time.perf_counter() - t0
            return parse_llm_json(raw_text), lat
        except Exception as e:
            time.sleep(1.5 * (attempt + 1))
    return {"crop": "錯誤", "status": "錯誤"}, time.perf_counter() - t0

def run_multi_ai_benchmark(val_dir: Path, target_samples: int = 400):
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    print(f"🚀 硬體加速裝置: {device} ({torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'})")

    idx_to_class = load_class_index()
    class_to_idx = {v: int(k) for k, v in idx_to_class.items()}
    num_classes = len(idx_to_class)

    conv_model = timm.create_model("convnext_small", num_classes=num_classes, pretrained=False)
    conv_model.load_state_dict(torch.load("convnext_plant_best.pth", map_location="cpu"))
    conv_model.to(device)
    conv_model.eval()

    # 均勻抽取 400 張測試樣本
    cases_by_folder = {}
    for folder_str in sorted(AIC_TO_PV.keys(), key=lambda x: int(x)):
        folder_path = val_dir / folder_str
        if not folder_path.exists():
            continue
        pv_class = AIC_TO_PV[folder_str]
        chinese_info = PLANTVILLAGE_TO_CHINESE.get(pv_class, {})
        cases_by_folder[folder_str] = {
            "pv": pv_class,
            "crop": chinese_info.get("crop", pv_class.split("___")[0]),
            "status": chinese_info.get("status", pv_class.split("___")[1]),
            "idx": class_to_idx.get(pv_class),
            "images": sorted(list(folder_path.glob("*.jpg")) + list(folder_path.glob("*.png")))
        }

    selected_cases = []
    img_idx = 0
    while len(selected_cases) < target_samples:
        added = False
        for f_str, info in cases_by_folder.items():
            if img_idx < len(info["images"]):
                selected_cases.append({
                    "path": info["images"][img_idx],
                    "folder": f_str,
                    "expected_crop": info["crop"],
                    "expected_status": info["status"],
                    "expected_pv": info["pv"],
                    "expected_idx": info["idx"]
                })
                added = True
                if len(selected_cases) >= target_samples:
                    break
        if not added:
            break
        img_idx += 1

    total = len(selected_cases)
    print(f"\n🏆【多模型級聯大對決 (Multi-AI Cascade Benchmark)】")
    print(f"📦 總樣本數: {total} 張 (均勻覆蓋全部 55 類病害)")
    print(f"🤖 對決模型陣列: Gemini 3.8 Flash vs OpenAI GPT-4o vs Claude Sonnet 5")

    ckpt_path = Path("artifacts/multi_ai_cascade_400_checkpoint.json")
    results_table = []
    processed_imgs = set()

    if ckpt_path.exists():
        try:
            with open(ckpt_path, "r", encoding="utf-8") as f:
                saved = json.load(f)
                if saved.get("total") == total:
                    results_table = saved.get("details", [])
                    processed_imgs = {r["image"] for r in results_table}
                    print(f"🔄 偵測到中斷存檔，成功接續 {len(results_table)} 張已完成樣本！直接從第 {len(results_table) + 1} 張開始...")
        except Exception:
            pass

    t_start = time.perf_counter()

    for idx, case in enumerate(selected_cases, 1):
        img_path = case["path"]
        if img_path.name in processed_imgs:
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
            conf, pred = probs.max(dim=1)
            local_conf = conf.item()
            local_idx = pred.item()
        local_lat_ms = (time.perf_counter() - t0) * 1000

        pred_pv = idx_to_class[local_idx]
        ch_info = PLANTVILLAGE_TO_CHINESE.get(pred_pv, {})
        local_crop = ch_info.get("crop", pred_pv.split("___")[0])
        local_status = ch_info.get("status", pred_pv.split("___")[1])
        local_correct = (local_idx == exp_idx)

        record = {
            "index": idx,
            "image": img_path.name,
            "folder": case["folder"],
            "expected_crop": exp_crop,
            "expected_status": exp_status,
            "local_pred_crop": local_crop,
            "local_pred_status": local_status,
            "local_confidence": round(local_conf, 4),
            "local_correct": local_correct,
            "local_latency_ms": round(local_lat_ms, 2),
            "triggered_fallback": False,
        }

        # 2. 判斷是否需要 Fallback
        if local_conf < 0.70:
            record["triggered_fallback"] = True
            with open(img_path, "rb") as f:
                b64_img = base64.b64encode(f.read()).decode("utf-8")

            # 同步併發向 3 大雲端模型請求
            with ThreadPoolExecutor(max_workers=3) as pool:
                fut_gemini = pool.submit(query_gemini, img_pil)
                fut_openai = pool.submit(query_openai, b64_img)
                fut_claude = pool.submit(query_claude, b64_img)

                gemini_res, gemini_lat = fut_gemini.result()
                openai_res, openai_lat = fut_openai.result()
                claude_res, claude_lat = fut_claude.result()

            # 驗證正確性
            gemini_corr = is_match(exp_crop, gemini_res["crop"], SYNONYMS) and is_match(exp_status, gemini_res["status"], SYNONYMS)
            openai_corr = is_match(exp_crop, openai_res["crop"], SYNONYMS) and is_match(exp_status, openai_res["status"], SYNONYMS)
            claude_corr = is_match(exp_crop, claude_res["crop"], SYNONYMS) and is_match(exp_status, claude_res["status"], SYNONYMS)

            record["gemini"] = {
                "crop": gemini_res["crop"],
                "status": gemini_res["status"],
                "correct": gemini_corr,
                "latency_s": round(gemini_lat, 2)
            }
            record["openai"] = {
                "crop": openai_res["crop"],
                "status": openai_res["status"],
                "correct": openai_corr,
                "latency_s": round(openai_lat, 2)
            }
            record["claude"] = {
                "crop": claude_res["crop"],
                "status": claude_res["status"],
                "correct": claude_corr,
                "latency_s": round(claude_lat, 2)
            }

            # 級聯結果：轉交雲端
            record["cascade_gemini_correct"] = gemini_corr
            record["cascade_openai_correct"] = openai_corr
            record["cascade_claude_correct"] = claude_corr
        else:
            # 級聯結果：本地高信心度快篩
            record["cascade_gemini_correct"] = local_correct
            record["cascade_openai_correct"] = local_correct
            record["cascade_claude_correct"] = local_correct

        results_table.append(record)

        # 列印進度
        if idx % 10 == 0 or idx == total or record["triggered_fallback"]:
            c_local = "✅" if record["local_correct"] else "❌"
            if record["triggered_fallback"]:
                g_c = "✅" if record["gemini"]["correct"] else "❌"
                o_c = "✅" if record["openai"]["correct"] else "❌"
                c_c = "✅" if record["claude"]["correct"] else "❌"
                print(f"[{idx:03d}/{total}] 葉片: {exp_crop}-{exp_status[:4]} | 本地:{c_local}({local_conf:.2f}) -> 轉交雲端 | Gem:{g_c} GPT4o:{o_c} Claude:{c_c}")
            else:
                print(f"[{idx:03d}/{total}] 葉片: {exp_crop}-{exp_status[:4]} | 本地快篩:{c_local}({local_conf:.2f}) [免調用API 66ms]")

        # 存檔 Checkpoint
        if idx % 10 == 0 or idx == total:
            with open(ckpt_path, "w", encoding="utf-8") as f:
                json.dump({"total": total, "details": results_table}, f, ensure_ascii=False, indent=2)

    # 統計報表
    total_samples = len(results_table)
    local_corr_cnt = sum(1 for r in results_table if r["local_correct"])
    fallback_cnt = sum(1 for r in results_table if r["triggered_fallback"])

    cas_gemini_corr = sum(1 for r in results_table if r["cascade_gemini_correct"])
    cas_openai_corr = sum(1 for r in results_table if r["cascade_openai_correct"])
    cas_claude_corr = sum(1 for r in results_table if r["cascade_claude_correct"])

    fb_gemini_corr = sum(1 for r in results_table if r.get("gemini", {}).get("correct", False))
    fb_openai_corr = sum(1 for r in results_table if r.get("openai", {}).get("correct", False))
    fb_claude_corr = sum(1 for r in results_table if r.get("claude", {}).get("correct", False))

    summary = {
        "total_samples": total_samples,
        "local_convnext_accuracy": round(local_corr_cnt / total_samples * 100, 2),
        "fallback_rate": round(fallback_cnt / total_samples * 100, 2),
        "api_saved_percentage": round((total_samples - fallback_cnt) / total_samples * 100, 2),
        "cascade_gemini_accuracy": round(cas_gemini_corr / total_samples * 100, 2),
        "cascade_openai_gpt4o_accuracy": round(cas_openai_corr / total_samples * 100, 2),
        "cascade_claude_sonnet_accuracy": round(cas_claude_corr / total_samples * 100, 2),
        "fallback_subset_results": {
            "total_fallback_samples": fallback_cnt,
            "gemini_accuracy": round(fb_gemini_corr / fallback_cnt * 100, 2) if fallback_cnt else 0,
            "openai_gpt4o_accuracy": round(fb_openai_corr / fallback_cnt * 100, 2) if fallback_cnt else 0,
            "claude_sonnet_accuracy": round(fb_claude_corr / fallback_cnt * 100, 2) if fallback_cnt else 0,
        }
    }

    report_path = Path("artifacts/multi_ai_cascade_400_final_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump({"summary": summary, "details": results_table}, f, ensure_ascii=False, indent=2)

    print("\n" + "="*60)
    print("🎯【400 張多模型級聯大對決最終成績公佈】")
    print(f"📊 總樣本數: {total_samples} 張 | 轉交雲端難題: {fallback_cnt} 張 (節省 {summary['api_saved_percentage']}% API 請求)")
    print(f"1️⃣ 本地 ConvNeXt 純端側:        {summary['local_convnext_accuracy']}% ({local_corr_cnt}/{total_samples})")
    print(f"2️⃣ 級聯 + Gemini 3.8 Flash:    {summary['cascade_gemini_accuracy']}% ({cas_gemini_corr}/{total_samples})")
    print(f"3️⃣ 級聯 + OpenAI GPT-4o:        {summary['cascade_openai_gpt4o_accuracy']}% ({cas_openai_corr}/{total_samples})")
    print(f"4️⃣ 級聯 + Claude Sonnet 5:      {summary['cascade_claude_sonnet_accuracy']}% ({cas_claude_corr}/{total_samples})")
    print("-" * 60)
    print("🔥【176 張極限疑難病害 (純雲端盲測對決)】")
    print(f"• Gemini 3.8 Flash:   {summary['fallback_subset_results']['gemini_accuracy']}% ({fb_gemini_corr}/{fallback_cnt})")
    print(f"• OpenAI GPT-4o:      {summary['fallback_subset_results']['openai_gpt4o_accuracy']}% ({fb_openai_corr}/{fallback_cnt})")
    print(f"• Claude Sonnet 5:    {summary['fallback_subset_results']['claude_sonnet_accuracy']}% ({fb_claude_corr}/{fallback_cnt})")
    print("="*60)

if __name__ == "__main__":
    val_path = Path(r"C:\Users\User\Downloads\val")
    run_multi_ai_benchmark(val_path, target_samples=400)
