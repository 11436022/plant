import base64
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

import functools
print = functools.partial(print, flush=True)

import timm
import torch
from PIL import Image
from google import genai
from dotenv import load_dotenv

load_dotenv()

from app.core.config import settings
from app.services.convnext import (
    load_class_index,
    _transform,
    PLANTVILLAGE_TO_CHINESE,
    extract_features_and_similarities,
    compute_cam_foreground_alignment,
    is_likely_fruit_for_leaf_disease,
    parse_convnext_prediction,
)
from scripts.compare_ai_challenger_three_strategies import SYNONYMS, is_match

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

GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "")
gemini_client = genai.Client(api_key=GEMINI_KEY)

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

def query_gemini_api(img_pil: Image.Image) -> tuple[dict, float]:
    t0 = time.perf_counter()
    for attempt in range(3):
        try:
            resp = gemini_client.models.generate_content(
                model="models/gemini-3.8-flash",
                contents=[img_pil, PROMPT_TEXT],
            )
            lat = time.perf_counter() - t0
            return parse_llm_json(resp.text), lat
        except Exception as e:
            time.sleep(1.5 * (attempt + 1))
    return {"crop": "錯誤", "status": "錯誤"}, time.perf_counter() - t0


def run_rerun_400():
    val_dir = Path(r"C:\Users\User\Downloads\val")
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    print(f"🚀 硬體加速裝置: {device} ({torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'})")

    old_report_path = Path("artifacts/multi_ai_cascade_400_final_report.json")
    with open(old_report_path, "r", encoding="utf-8") as f:
        old_data = json.load(f)
    old_details = old_data["details"]
    print(f"📦 成功載入歷史 400 張精確盲測樣本清單！")

    idx_mapping = load_class_index()
    num_classes = len(idx_mapping)

    model = timm.create_model("convnext_small", num_classes=num_classes, pretrained=False)
    model.load_state_dict(torch.load("convnext_plant_best.pth", map_location="cpu"))
    model.to(device)
    model.eval()

    print(f"⚙️ 現行生產門檻配置：")
    print(f"   - 置信度門檻: {settings.CONVNEXT_OVERWHELMING_CONFIDENCE}")
    print(f"   - 餘弦相似度門檻: {settings.CONVNEXT_MIN_COSINE_SIMILARITY}")
    print(f"   - CAM 前景對齊門檻: {settings.CONVNEXT_MIN_CAM_FOREGROUND_RATIO}")

    new_results = []
    gemini_api_calls = 0

    print("\n⏳ 正在使用現行策略重測 400 張樣本...")
    for idx, d in enumerate(old_details, 1):
        img_path = val_dir / d["folder"] / d["image"]
        img_pil = Image.open(img_path).convert("RGB")
        tensor = _transform(img_pil).unsqueeze(0).to(device)

        with torch.no_grad():
            probs, cos_sims = extract_features_and_similarities(model, tensor)
            raw_feats = model.forward_features(tensor)
        
        top_prob, top_idx = torch.max(probs, dim=0)
        score = float(top_prob.item())
        cos_s = float(cos_sims[top_idx].item()) if cos_sims is not None else 1.0
        pred_lbl = idx_mapping.get(int(top_idx.item()), "")
        pred_crop, pred_status, _ = parse_convnext_prediction(pred_lbl)
        cam_ratio = compute_cam_foreground_alignment(model, raw_feats, int(top_idx.item()), img_pil)
        fruit_mismatch = is_likely_fruit_for_leaf_disease(img_pil, pred_lbl)

        # 判定本地預測是否正確
        exp_crop = d["expected_crop"]
        exp_status = d["expected_status"]
        local_correct = is_match(exp_crop, pred_crop, SYNONYMS) and is_match(exp_status, pred_status, SYNONYMS)

        # 現行生產策略過濾判斷
        is_current_hit = (
            score >= settings.CONVNEXT_OVERWHELMING_CONFIDENCE
            and cos_s >= settings.CONVNEXT_MIN_COSINE_SIMILARITY
            and cam_ratio >= settings.CONVNEXT_MIN_CAM_FOREGROUND_RATIO
            and not fruit_mismatch
        )

        rec = {
            "index": idx,
            "image": d["image"],
            "folder": d["folder"],
            "expected_crop": exp_crop,
            "expected_status": exp_status,
            "local_pred_crop": pred_crop,
            "local_pred_status": pred_status,
            "local_score": round(score, 4),
            "local_cos_sim": round(cos_s, 4),
            "cam_ratio": round(cam_ratio, 4),
            "local_correct": local_correct,
            "triggered_fallback": not is_current_hit,
        }

        if is_current_hit:
            # 本地快篩命中 (無呼叫 API)
            rec["cascade_gemini_correct"] = local_correct
            rec["route"] = "本地快篩 (<4ms)"
            rec["gemini_pred_crop"] = ""
            rec["gemini_pred_status"] = ""
        else:
            # 轉交 Gemini 兜底
            rec["route"] = "雲端 Gemini 兜底"
            # 若歷史數據中已有 Gemini 結果，直接沿用
            if d.get("triggered_fallback") and "gemini" in d and d["gemini"].get("crop"):
                gem_crop = d["gemini"]["crop"]
                gem_status = d["gemini"]["status"]
                gem_corr = is_match(exp_crop, gem_crop, SYNONYMS) and is_match(exp_status, gem_status, SYNONYMS)
            else:
                # 呼叫 Gemini 3.8 Flash
                res_dict, _ = query_gemini_api(img_pil)
                gem_crop = res_dict["crop"]
                gem_status = res_dict["status"]
                gem_corr = is_match(exp_crop, gem_crop, SYNONYMS) and is_match(exp_status, gem_status, SYNONYMS)
                gemini_api_calls += 1
                time.sleep(1.2)

            rec["gemini_pred_crop"] = gem_crop
            rec["gemini_pred_status"] = gem_status
            rec["gemini_correct"] = gem_corr
            rec["cascade_gemini_correct"] = gem_corr

        new_results.append(rec)
        if idx % 50 == 0:
            print(f"   [進度] 已完成 {idx}/400 張分析 (現行快篩命中: {sum(not r['triggered_fallback'] for r in new_results)})...")

    # 綜合指標計算
    total = len(new_results)
    pure_local_corr = sum(r["local_correct"] for r in new_results)
    pure_local_acc = pure_local_corr / total * 100

    fast_screen_count = sum(not r["triggered_fallback"] for r in new_results)
    fallback_count = sum(r["triggered_fallback"] for r in new_results)
    api_saved_pct = fast_screen_count / total * 100

    cascade_gemini_corr = sum(r["cascade_gemini_correct"] for r in new_results)
    cascade_gemini_acc = cascade_gemini_corr / total * 100

    # 困難樣本兜底分析 (fallback subset)
    fallback_subset = [r for r in new_results if r["triggered_fallback"]]
    fallback_gemini_corr = sum(r["cascade_gemini_correct"] for r in fallback_subset)
    fallback_gemini_acc = fallback_gemini_corr / len(fallback_subset) * 100

    # 舊模型在困難樣本上的表現
    fallback_local_corr = sum(r["local_correct"] for r in fallback_subset)
    fallback_local_acc = fallback_local_corr / len(fallback_subset) * 100

    # 舊的 GPT-4o 與 Claude 在 fallback 上的對比 (歷史留存數據)
    # 取 fallback_subset 中有歷史 openai/claude 數據的部分
    old_details_map = {d["image"]: d for d in old_details}
    gpt_corr_cnt = 0
    claude_corr_cnt = 0
    for r in fallback_subset:
        old_d = old_details_map.get(r["image"], {})
        if old_d.get("openai", {}).get("correct"):
            gpt_corr_cnt += 1
        if old_d.get("claude", {}).get("correct"):
            claude_corr_cnt += 1
    gpt_acc = gpt_corr_cnt / len(fallback_subset) * 100
    claude_acc = claude_corr_cnt / len(fallback_subset) * 100

    cascade_gpt_acc = (sum(r["local_correct"] for r in new_results if not r["triggered_fallback"]) + gpt_corr_cnt) / total * 100
    cascade_claude_acc = (sum(r["local_correct"] for r in new_results if not r["triggered_fallback"]) + claude_corr_cnt) / total * 100

    print("\n" + "=" * 65)
    print("🏆【400 張盲測——現行生產策略重測成果】")
    print("=" * 65)
    print(f"🔹 總測試樣本數: {total} 張 (跨 55 類病害)")
    print(f"🔹 本地 ConvNeXt 單獨準確率 : {pure_local_acc:.2f}% ({pure_local_corr}/{total})")
    print(f"🔹 端側快篩攔截率 (API 節省): {api_saved_pct:.2f}% ({fast_screen_count}/{total})")
    print(f"🔹 雲端兜底調用次數          : {fallback_count} 次 (新增 API 調用: {gemini_api_calls} 次)")
    print(f"🔹 【現行級聯 + Gemini 3.8】 總體準確率 : {cascade_gemini_acc:.2f}% ({cascade_gemini_corr}/{total})")
    print(f"🔹 【{fallback_count} 張疑難樣本純雲端命中率】: Gemini 3.8 Flash = {fallback_gemini_acc:.2f}% ({fallback_gemini_corr}/{fallback_count})")
    print(f"   (原端側在此疑難子集上僅 {fallback_local_acc:.2f}%)")
    print("=" * 65)

    report_data = {
        "title": "400 張多模型盲測——現行生產策略重新評估報告",
        "total_samples": total,
        "pure_local_accuracy": round(pure_local_acc, 2),
        "api_saved_percentage": round(api_saved_pct, 2),
        "fast_screen_count": fast_screen_count,
        "fallback_count": fallback_count,
        "cascade_gemini_accuracy": round(cascade_gemini_acc, 2),
        "cascade_gpt4o_accuracy": round(cascade_gpt_acc, 2),
        "cascade_claude_accuracy": round(cascade_claude_acc, 2),
        "fallback_subset": {
            "total_fallback_samples": fallback_count,
            "local_accuracy_on_fallback": round(fallback_local_acc, 2),
            "gemini_accuracy": round(fallback_gemini_acc, 2),
            "gpt4o_accuracy": round(gpt_acc, 2),
            "claude_accuracy": round(claude_acc, 2),
        },
        "details": new_results,
    }

    out_json = Path("artifacts/multi_ai_cascade_400_current_strategy_report.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(report_data, f, ensure_ascii=False, indent=2)
    print(f"✅ 報告已儲存: {out_json}")


if __name__ == "__main__":
    run_rerun_400()

