import base64
import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from threading import Lock

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

import functools
print = functools.partial(print, flush=True)

from openai import OpenAI
import anthropic

from scripts.compare_ai_challenger_three_strategies import SYNONYMS

# 增強同義詞表
SYNONYMS.update({
    "玉米": ["玉米", "玉蜀黍", "苞米", "maize", "corn"],
    "蘋果": ["蘋果", "苹果", "apple"],
    "葡萄": ["葡萄", "grape"],
    "櫻桃": ["櫻桃", "樱桃", "車厘子", "cherry"],
    "柑橘": ["柑橘", "柑桔", "橘子", "橙子", "柑", "桔", "橙", "citrus", "orange"],
    "桃": ["桃", "桃子", "peach"],
    "甜椒": ["甜椒", "彩椒", "青椒", "辣椒", "椒", "bell pepper", "pepper"],
    "馬鈴薯": ["馬鈴薯", "土豆", "洋芋", "potato"],
    "草莓": ["草莓", "strawberry"],
    "番茄": ["番茄", "西紅柿", "tomato"],
    "大豆": ["大豆", "黃豆", "毛豆", "soybean"],
    "南瓜": ["南瓜", "squash", "pumpkin"],
    "灰斑病": ["灰斑病", "尾孢菌葉斑病", "角斑病", "灰斑", "cercospora", "gray leaf spot"],
    "葉斑病": ["葉斑病", "彎孢葉斑病", "斑點病", "葉斑", "curvularia leaf spot"],
    "白粉病": ["白粉病", "白粉", "powdery mildew"],
    "黑星病": ["黑星病", "瘡痂病", "黑星", "scab"],
    "黑腐病": ["黑腐病", "黑腐", "black rot"],
    "黑痘病": ["黑痘病", "黑痘", "瘡痂病", "esca", "measles"],
    "褐斑病": ["褐斑病", "褐斑", "褐葉斑", "leaf blight", "isariopsis"],
    "銹病": ["銹病", "鏽病", "銹", "鏽", "rust"],
    "早疫病": ["早疫病", "輪紋病", "早疫", "early blight"],
    "晚疫病": ["晚疫病", "疫病", "晚疫", "late blight"],
    "葉黴病": ["葉黴病", "葉霉病", "葉黴", "leaf mold"],
    "斑枯病": ["斑枯病", "斑點病", "靶斑病", "枯斑病", "septoria", "target spot"],
    "黃龍病": ["黃龍病", "柑橘黃龍病", "黃龍", "greening", "hlb"],
    "健康": ["健康", "正常", "無病害", "healthy"],
})

def is_match_term(expected: str, predicted: str, synonyms_dict: dict) -> bool:
    if not predicted or predicted in ["無法解析", "錯誤", "未知"]:
        return False
    if expected in predicted or predicted in expected:
        return True
    expected_syns = synonyms_dict.get(expected, [expected])
    predicted_syns = synonyms_dict.get(predicted, [predicted])
    for s1 in expected_syns:
        for s2 in predicted_syns:
            if s1 in predicted or s2 in expected or s1 == s2:
                return True
    return False

# 金鑰設定 (從環境變數或用戶提供之金鑰)
OPENAI_KEY = os.environ.get("OPENAI_API_KEY", "")
CLAUDE_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

openai_client = OpenAI(api_key=OPENAI_KEY)
anthropic_client = anthropic.Anthropic(api_key=CLAUDE_KEY)

PROMPT_TEXT = (
    "你是一位頂尖的農業病理學家與植物保護專家。請仔細觀察這張照片中的葉片，辨識其作物種類與健康狀態/病害名稱。\n"
    "請嚴格以繁體中文單層 JSON 格式回答，不要有任何多餘贅字或 markdown 包裹以外的文字：\n"
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
                "crop": str(d.get("crop", d.get("crop_name", "無法解析"))).strip(),
                "status": str(d.get("status", d.get("status_name", "無法解析"))).strip()
            }
        except Exception:
            pass
    return {"crop": "無法解析", "status": "無法解析"}

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
                max_tokens=150,
                timeout=30.0
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
                timeout=30.0,
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
            raw_text = ""
            for block in resp.content:
                if hasattr(block, "text"):
                    raw_text += block.text
            lat = time.perf_counter() - t0
            return parse_llm_json(raw_text), lat
        except Exception as e:
            time.sleep(1.5 * (attempt + 1))
    return {"crop": "錯誤", "status": "錯誤"}, time.perf_counter() - t0

def process_one_sample(sample: dict, val_dir: Path) -> dict:
    img_path = val_dir / sample["folder"] / sample["image"]
    with open(img_path, "rb") as f:
        b64_img = base64.b64encode(f.read()).decode("utf-8")

    exp_crop = sample["expected_crop"]
    exp_status = sample["expected_status"]

    oa_res, oa_lat = query_openai(b64_img)
    cl_res, cl_lat = query_claude(b64_img)

    oa_crop_match = is_match_term(exp_crop, oa_res["crop"], SYNONYMS)
    oa_stat_match = is_match_term(exp_status, oa_res["status"], SYNONYMS)
    oa_correct = oa_crop_match and oa_stat_match

    cl_crop_match = is_match_term(exp_crop, cl_res["crop"], SYNONYMS)
    cl_stat_match = is_match_term(exp_status, cl_res["status"], SYNONYMS)
    cl_correct = cl_crop_match and cl_stat_match

    return {
        "image": sample["image"],
        "folder": sample["folder"],
        "expected_crop": exp_crop,
        "expected_status": exp_status,
        "openai": {
            "crop": oa_res["crop"],
            "status": oa_res["status"],
            "crop_correct": oa_crop_match,
            "status_correct": oa_stat_match,
            "correct": oa_correct,
            "latency_s": round(oa_lat, 2)
        },
        "claude": {
            "crop": cl_res["crop"],
            "status": cl_res["status"],
            "crop_correct": cl_crop_match,
            "status_correct": cl_stat_match,
            "correct": cl_correct,
            "latency_s": round(cl_lat, 2)
        }
    }

def main():
    val_dir = Path(r"C:\Users\User\Downloads\val")
    report_path = Path("artifacts/multi_ai_cascade_400_current_strategy_report.json")
    ckpt_path = Path("artifacts/openai_claude_209_checkpoint.json")

    with open(report_path, "r", encoding="utf-8") as f:
        report_data = json.load(f)

    fallback_samples = [d for d in report_data["details"] if d.get("triggered_fallback")]
    print(f"📦 載入現行生產策略兜底樣本：共 {len(fallback_samples)} 張困難邊界樣本")

    # 讀取現有 checkpoint
    checkpoint = {}
    if ckpt_path.exists():
        try:
            with open(ckpt_path, "r", encoding="utf-8") as f:
                checkpoint = json.load(f)
            print(f"🔄 偵測到 Checkpoint，已完成 {len(checkpoint)}/{len(fallback_samples)} 張樣本")
        except Exception:
            checkpoint = {}

    to_process = [s for s in fallback_samples if s["image"] not in checkpoint]
    print(f"🚀 本次需呼叫 API 測評數量：{len(to_process)} 張")

    ckpt_lock = Lock()
    completed_count = len(checkpoint)

    if to_process:
        print("⚡ 啟動多執行緒並發評測 (3 Workers)...")
        with ThreadPoolExecutor(max_workers=3) as pool:
            futures = {pool.submit(process_one_sample, s, val_dir): s for s in to_process}
            for fut in as_completed(futures):
                s = futures[fut]
                try:
                    res = fut.result()
                    with ckpt_lock:
                        checkpoint[res["image"]] = res
                        completed_count += 1
                        oa = res["openai"]
                        cl = res["claude"]
                        oa_mark = "✅" if oa["correct"] else "❌"
                        cl_mark = "✅" if cl["correct"] else "❌"
                        print(f"[{completed_count:03d}/209] {res['expected_crop']}-{res['expected_status'][:4]} | GPT-4o: {oa_mark} ({oa['crop']}-{oa['status']}) | Claude: {cl_mark} ({cl['crop']}-{cl['status']})")
                        
                        if completed_count % 10 == 0 or completed_count == len(fallback_samples):
                            with open(ckpt_path, "w", encoding="utf-8") as f_out:
                                json.dump(checkpoint, f_out, ensure_ascii=False, indent=2)
                except Exception as e:
                    print(f"❌ 評測失敗 {s['image']}: {e}")

    # 確保最終 checkpoint 寫入
    with open(ckpt_path, "w", encoding="utf-8") as f_out:
        json.dump(checkpoint, f_out, ensure_ascii=False, indent=2)

    print("\n🎉 全部 209 張困難兜底樣本 OpenAI GPT-4o & Claude 實時評測完成！開始統計整合...")

    # 將結果合併回 details
    details = report_data["details"]
    for d in details:
        img_name = d["image"]
        if d.get("triggered_fallback"):
            cp_data = checkpoint.get(img_name, {})
            oa_info = cp_data.get("openai", {"crop": "", "status": "", "correct": False, "latency_s": 0.0})
            cl_info = cp_data.get("claude", {"crop": "", "status": "", "correct": False, "latency_s": 0.0})
            d["openai"] = oa_info
            d["claude"] = cl_info
            d["cascade_openai_correct"] = oa_info["correct"]
            d["cascade_claude_correct"] = cl_info["correct"]
        else:
            # 快篩命中，沿用本地預測
            d["cascade_openai_correct"] = d["local_correct"]
            d["cascade_claude_correct"] = d["local_correct"]

    # 指標統計
    total_samples = len(details)
    fast_screens = [d for d in details if not d.get("triggered_fallback")]
    fallbacks = [d for d in details if d.get("triggered_fallback")]

    pure_local_corr = sum(1 for d in details if d["local_correct"])
    pure_local_acc = round(pure_local_corr / total_samples * 100, 2)

    fast_screen_corr = sum(1 for d in fast_screens if d["local_correct"])
    fallback_local_corr = sum(1 for d in fallbacks if d["local_correct"])

    cas_gemini_corr = sum(1 for d in details if d["cascade_gemini_correct"])
    cas_openai_corr = sum(1 for d in details if d["cascade_openai_correct"])
    cas_claude_corr = sum(1 for d in details if d["cascade_claude_correct"])

    fb_gemini_corr = sum(1 for d in fallbacks if d["cascade_gemini_correct"])
    fb_openai_corr = sum(1 for d in fallbacks if d["cascade_openai_correct"])
    fb_claude_corr = sum(1 for d in fallbacks if d["cascade_claude_correct"])

    # 作物與病害分項正確率 (在 209 難題上)
    oa_crop_corr = sum(1 for d in fallbacks if d.get("openai", {}).get("crop_correct", False))
    oa_stat_corr = sum(1 for d in fallbacks if d.get("openai", {}).get("status_correct", False))
    cl_crop_corr = sum(1 for d in fallbacks if d.get("claude", {}).get("crop_correct", False))
    cl_stat_corr = sum(1 for d in fallbacks if d.get("claude", {}).get("status_correct", False))

    # 有害兜底分析 (Negative Transfer Breakdown)
    # fixed: 本地原本錯，雲端救回
    # overwrote: 本地原本對，雲端改錯
    # net: 淨貢獻 (fixed - overwrote)
    def calc_transfer(pred_key):
        fixed = 0
        overwrote = 0
        for d in fallbacks:
            loc = d["local_correct"]
            cld = d[pred_key]
            if not loc and cld:
                fixed += 1
            elif loc and not cld:
                overwrote += 1
        return fixed, overwrote, fixed - overwrote

    g_fix, g_ovw, g_net = calc_transfer("cascade_gemini_correct")
    o_fix, o_ovw, o_net = calc_transfer("cascade_openai_correct")
    c_fix, c_ovw, c_net = calc_transfer("cascade_claude_correct")

    report_data["pure_local_accuracy"] = pure_local_acc
    report_data["cascade_gemini_accuracy"] = round(cas_gemini_corr / total_samples * 100, 2)
    report_data["cascade_gpt4o_accuracy"] = round(cas_openai_corr / total_samples * 100, 2)
    report_data["cascade_claude_accuracy"] = round(cas_claude_corr / total_samples * 100, 2)

    report_data["fallback_subset"] = {
        "total_fallback_samples": len(fallbacks),
        "local_accuracy_on_fallback": round(fallback_local_corr / len(fallbacks) * 100, 2),
        "gemini_accuracy": round(fb_gemini_corr / len(fallbacks) * 100, 2),
        "gpt4o_accuracy": round(fb_openai_corr / len(fallbacks) * 100, 2),
        "claude_accuracy": round(fb_claude_corr / len(fallbacks) * 100, 2),
        "gemini_correct_count": fb_gemini_corr,
        "gpt4o_correct_count": fb_openai_corr,
        "claude_correct_count": fb_claude_corr,
        "gpt4o_crop_accuracy": round(oa_crop_corr / len(fallbacks) * 100, 2),
        "gpt4o_status_accuracy": round(oa_stat_corr / len(fallbacks) * 100, 2),
        "claude_crop_accuracy": round(cl_crop_corr / len(fallbacks) * 100, 2),
        "claude_status_accuracy": round(cl_stat_corr / len(fallbacks) * 100, 2),
        "negative_transfer": {
            "gemini": {"fixed": g_fix, "overwrote": g_ovw, "net": g_net},
            "gpt4o": {"fixed": o_fix, "overwrote": o_ovw, "net": o_net},
            "claude": {"fixed": c_fix, "overwrote": c_ovw, "net": c_net}
        }
    }

    report_data["details"] = details

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report_data, f, ensure_ascii=False, indent=2)

    print("\n================= 📊 最終實測綜合報告 =================")
    print(f"📦 總樣本數: {total_samples} (端側快篩: {len(fast_screens)}, 雲端兜底: {len(fallbacks)})")
    print(f"🔹 純端側 ConvNeXt 準確率: {pure_local_acc}% ({pure_local_corr}/{total_samples})")
    print(f"🏆 級聯 + Gemini 3.8 準確率: {report_data['cascade_gemini_accuracy']}% ({cas_gemini_corr}/{total_samples}) [淨增加 +{g_net} 題]")
    print(f"🟧 級聯 + GPT-4o 準確率:     {report_data['cascade_gpt4o_accuracy']}% ({cas_openai_corr}/{total_samples}) [淨變化 {o_net:+d} 題]")
    print(f"🟪 級聯 + Claude Sonnet 5:  {report_data['cascade_claude_accuracy']}% ({cas_claude_corr}/{total_samples}) [淨變化 {c_net:+d} 題]")
    print("----------------- 209 張疑難邊界樣本純對決 -----------------")
    print(f"端側原始表現: {fallback_local_corr}/209 ({report_data['fallback_subset']['local_accuracy_on_fallback']}%)")
    print(f"Gemini 3.8:  {fb_gemini_corr}/209 ({report_data['fallback_subset']['gemini_accuracy']}%) [救回 {g_fix}, 改錯 {g_ovw}]")
    print(f"OpenAI GPT4o: {fb_openai_corr}/209 ({report_data['fallback_subset']['gpt4o_accuracy']}%) [救回 {o_fix}, 改錯 {o_ovw}]")
    print(f"Claude S5:    {fb_claude_corr}/209 ({report_data['fallback_subset']['claude_accuracy']}%) [救回 {c_fix}, 改錯 {c_ovw}]")
    print("=========================================================\n")

if __name__ == "__main__":
    main()

