import argparse
import json
import os
import random
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
from torchvision import transforms
from google import genai
from dotenv import load_dotenv

import functools
print = functools.partial(print, flush=True)

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
    get_convnext_model,
)
from scripts.compare_ai_challenger_three_strategies import SYNONYMS, is_match

# 完整的 AI Challenger 61 類中英與標準作物病害對照表
AIC_61_MAPPING = {
    "0": {"crop": "蘋果", "status": "健康", "pv": "Apple___healthy"},
    "1": {"crop": "蘋果", "status": "黑星病", "pv": "Apple___Apple_scab"},
    "2": {"crop": "蘋果", "status": "黑星病", "pv": "Apple___Apple_scab"},
    "3": {"crop": "蘋果", "status": "灰斑病", "pv": "Apple___Frogeye_Spot"},
    "4": {"crop": "蘋果", "status": "銹病", "pv": "Apple___Cedar_apple_rust"},
    "5": {"crop": "蘋果", "status": "銹病", "pv": "Apple___Cedar_apple_rust"},
    "6": {"crop": "櫻桃", "status": "健康", "pv": "Cherry_(including_sour)___healthy"},
    "7": {"crop": "櫻桃", "status": "白粉病", "pv": "Cherry_(including_sour)___Powdery_mildew"},
    "8": {"crop": "櫻桃", "status": "白粉病", "pv": "Cherry_(including_sour)___Powdery_mildew"},
    "9": {"crop": "玉米", "status": "健康", "pv": "Corn_(maize)___healthy"},
    "10": {"crop": "玉米", "status": "灰斑病", "pv": "Corn_(maize)___Cercospora_leaf_spot Gray_leaf_spot"},
    "11": {"crop": "玉米", "status": "灰斑病", "pv": "Corn_(maize)___Cercospora_leaf_spot Gray_leaf_spot"},
    "12": {"crop": "玉米", "status": "銹病", "pv": "Corn_(maize)___Common_rust_"},
    "13": {"crop": "玉米", "status": "銹病", "pv": "Corn_(maize)___Common_rust_"},
    "14": {"crop": "玉米", "status": "葉斑病", "pv": "Corn_(maize)___Curvularia_leaf_spot"},
    "15": {"crop": "玉米", "status": "葉斑病", "pv": "Corn_(maize)___Curvularia_leaf_spot"},
    "16": {"crop": "玉米", "status": "花葉病毒病", "pv": "Corn_(maize)___Maize_dwarf_mosaic_virus"},
    "17": {"crop": "葡萄", "status": "健康", "pv": "Grape___healthy"},
    "18": {"crop": "葡萄", "status": "黑腐病", "pv": "Grape___Black_rot"},
    "19": {"crop": "葡萄", "status": "黑腐病", "pv": "Grape___Black_rot"},
    "20": {"crop": "葡萄", "status": "黑痘病", "pv": "Grape___Esca_(Black_Measles)"},
    "21": {"crop": "葡萄", "status": "黑痘病", "pv": "Grape___Esca_(Black_Measles)"},
    "22": {"crop": "葡萄", "status": "褐斑病", "pv": "Grape___Leaf_blight_(Isariopsis_Leaf_Spot)"},
    "23": {"crop": "葡萄", "status": "褐斑病", "pv": "Grape___Leaf_blight_(Isariopsis_Leaf_Spot)"},
    "24": {"crop": "柑橘", "status": "黃龍病", "pv": "Orange___Haunglongbing_(Citrus_greening)"},
    "25": {"crop": "柑橘", "status": "黃龍病", "pv": "Orange___Haunglongbing_(Citrus_greening)"},
    "26": {"crop": "柑橘", "status": "黃龍病", "pv": "Orange___Haunglongbing_(Citrus_greening)"},
    "27": {"crop": "桃", "status": "健康", "pv": "Peach___healthy"},
    "28": {"crop": "桃", "status": "細菌性穿孔病", "pv": "Peach___Bacterial_spot"},
    "29": {"crop": "桃", "status": "細菌性穿孔病", "pv": "Peach___Bacterial_spot"},
    "30": {"crop": "甜椒", "status": "健康", "pv": "Pepper,_bell___healthy"},
    "31": {"crop": "甜椒", "status": "細菌性斑點病", "pv": "Pepper,_bell___Bacterial_spot"},
    "32": {"crop": "甜椒", "status": "細菌性斑點病", "pv": "Pepper,_bell___Bacterial_spot"},
    "33": {"crop": "馬鈴薯", "status": "健康", "pv": "Potato___healthy"},
    "34": {"crop": "馬鈴薯", "status": "早疫病", "pv": "Potato___Early_blight"},
    "35": {"crop": "馬鈴薯", "status": "早疫病", "pv": "Potato___Early_blight"},
    "36": {"crop": "馬鈴薯", "status": "晚疫病", "pv": "Potato___Late_blight"},
    "37": {"crop": "馬鈴薯", "status": "晚疫病", "pv": "Potato___Late_blight"},
    "38": {"crop": "草莓", "status": "健康", "pv": "Strawberry___healthy"},
    "39": {"crop": "草莓", "status": "葉焦病", "pv": "Strawberry___Leaf_scorch"},
    "40": {"crop": "草莓", "status": "葉焦病", "pv": "Strawberry___Leaf_scorch"},
    "41": {"crop": "番茄", "status": "健康", "pv": "Tomato___healthy"},
    "42": {"crop": "番茄", "status": "白粉病", "pv": "Tomato___Powdery_mildew"},
    "43": {"crop": "番茄", "status": "白粉病", "pv": "Tomato___Powdery_mildew"},
    "44": {"crop": "番茄", "status": "細菌性斑點病", "pv": "Tomato___Bacterial_spot"},
    "45": {"crop": "番茄", "status": "細菌性斑點病", "pv": "Tomato___Bacterial_spot"},
    "46": {"crop": "番茄", "status": "早疫病", "pv": "Tomato___Early_blight"},
    "47": {"crop": "番茄", "status": "早疫病", "pv": "Tomato___Early_blight"},
    "48": {"crop": "番茄", "status": "晚疫病", "pv": "Tomato___Late_blight"},
    "49": {"crop": "番茄", "status": "晚疫病", "pv": "Tomato___Late_blight"},
    "50": {"crop": "番茄", "status": "葉黴病", "pv": "Tomato___Leaf_Mold"},
    "51": {"crop": "番茄", "status": "葉黴病", "pv": "Tomato___Leaf_Mold"},
    "52": {"crop": "番茄", "status": "斑枯病", "pv": "Tomato___Target_Spot"},
    "53": {"crop": "番茄", "status": "斑枯病", "pv": "Tomato___Target_Spot"},
    "54": {"crop": "番茄", "status": "斑枯病", "pv": "Tomato___Septoria_leaf_spot"},
    "55": {"crop": "番茄", "status": "斑枯病", "pv": "Tomato___Septoria_leaf_spot"},
    "56": {"crop": "番茄", "status": "二點葉蟎", "pv": "Tomato___Spider_mites Two-spotted_spider_mite"},
    "57": {"crop": "番茄", "status": "二點葉蟎", "pv": "Tomato___Spider_mites Two-spotted_spider_mite"},
    "58": {"crop": "番茄", "status": "黃化捲葉病毒病", "pv": "Tomato___Tomato_Yellow_Leaf_Curl_Virus"},
    "59": {"crop": "番茄", "status": "黃化捲葉病毒病", "pv": "Tomato___Tomato_Yellow_Leaf_Curl_Virus"},
    "60": {"crop": "番茄", "status": "嵌紋病毒病", "pv": "Tomato___Tomato_mosaic_virus"},
}

# 補充更寬容的作物與病害同義詞表
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
    # 病害同義詞補充
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

FREE_KEY_POOL = [
    k.strip() for k in os.environ.get("FREE_KEY_POOL", os.environ.get("GEMINI_API_KEY", "")).split(",") if k.strip()
]
PAID_KEY_BLACKLIST = os.environ.get("PAID_KEY_BLACKLIST", "")


class KeyPoolManager:
    """智慧免費金鑰輪替池"""
    def __init__(self, keys: list[str]):
        self.keys = [k for k in keys if k != PAID_KEY_BLACKLIST]
        self.clients = [genai.Client(api_key=k) for k in self.keys]
        self.current_idx = 0
        print(f"🔒 金鑰池初始化成功：共掛載 {len(self.keys)} 組免費金鑰")

    def get_client(self):
        client = self.clients[self.current_idx]
        key_short = self.keys[self.current_idx][:8] + "..." + self.keys[self.current_idx][-4:]
        return client, self.current_idx, key_short

    def rotate_next(self):
        self.current_idx = (self.current_idx + 1) % len(self.keys)
        new_key = self.keys[self.current_idx][:8] + "..." + self.keys[self.current_idx][-4:]
        print(f"🔄 自動輪替至第 {self.current_idx + 1} 組免費金鑰 ({new_key})")


def sample_stratified_1000(val_dir: Path, target_total: int = 1000, seed: int = 42) -> list[dict]:
    """從 61 個類別資料夾進行分層均勻隨機抽樣，確保全品種公平覆蓋"""
    random.seed(seed)
    folders = sorted([d for d in val_dir.iterdir() if d.is_dir() and d.name in AIC_61_MAPPING], key=lambda x: int(x.name))
    
    folder_imgs = {}
    for f in folders:
        imgs = sorted(list(f.glob("*.jpg")) + list(f.glob("*.png")) + list(f.glob("*.JPG")))
        folder_imgs[f.name] = imgs

    # 計算各資料夾配額 (基本 16 張，部分 17 張)
    quota = {}
    remaining = target_total
    for f_name, imgs in folder_imgs.items():
        base = 16
        take = min(base, len(imgs))
        quota[f_name] = take
        remaining -= take

    # 將剩餘名額均勻分給有充足圖片的資料夾
    f_keys = list(folder_imgs.keys())
    idx = 0
    while remaining > 0:
        k = f_keys[idx % len(f_keys)]
        if quota[k] < len(folder_imgs[k]):
            quota[k] += 1
            remaining -= 1
        idx += 1

    selected_samples = []
    for f_name in sorted(folder_imgs.keys(), key=lambda x: int(x)):
        imgs = folder_imgs[f_name]
        n_take = quota[f_name]
        sampled = random.sample(imgs, n_take)
        meta = AIC_61_MAPPING[f_name]
        for img_p in sampled:
            selected_samples.append({
                "path": img_p,
                "folder": f_name,
                "expected_crop": meta["crop"],
                "expected_status": meta["status"],
                "expected_pv": meta["pv"],
            })

    print(f"📦 分層抽樣完成：共選取 {len(selected_samples)} 張樣本，跨 {len(folder_imgs)} 類病害全覆蓋！")
    return selected_samples


GEMINI_PROMPT_TEXT = (
    "你是一位頂尖的植物病理學家。請仔細觀察這張照片中的葉片，辨識其作物種類與健康狀態/病害名稱。\n"
    "請嚴格以繁體中文單層 JSON 格式回答，不要有任何多餘贅字或 markdown 包裹以外的文字：\n"
    '{"crop_name": "作物名稱", "status_name": "病害名稱或健康", "confidence": 0.85}\n'
    "範例：\n"
    '{"crop_name": "番茄", "status_name": "早疫病", "confidence": 0.95}\n'
    '{"crop_name": "蘋果", "status_name": "健康", "confidence": 0.98}'
)

def parse_gemini_response(raw_text: str) -> dict:
    if not raw_text:
        return {"crop_name": "無法解析", "status_name": "無法解析", "confidence": 0.0}
    clean = re.sub(r"^```json\s*", "", raw_text.strip(), flags=re.MULTILINE)
    clean = re.sub(r"^```\s*", "", clean, flags=re.MULTILINE).strip()
    m = re.search(r"\{.*?\}", clean, re.DOTALL)
    if m:
        try:
            d = json.loads(m.group(0))
            return {
                "crop_name": str(d.get("crop_name", d.get("crop", "無法解析"))).strip(),
                "status_name": str(d.get("status_name", d.get("status", "無法解析"))).strip(),
                "confidence": float(d.get("confidence", 0.8)),
            }
        except Exception:
            pass
    return {"crop_name": "無法解析", "status_name": "無法解析", "confidence": 0.0}


def run_benchmark(val_dir: Path, delay_seconds: float = 1.0):
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    print(f"🚀 硬體加速裝置: {device} ({torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'})")

    idx_mapping = load_class_index()
    num_classes = len(idx_mapping)

    # 載入本地微調模型
    model = timm.create_model("convnext_small", num_classes=num_classes, pretrained=False)
    model.load_state_dict(torch.load("convnext_plant_best.pth", map_location="cpu"))
    model.to(device)
    model.eval()

    # 1. 抽樣 1,000 張
    samples = sample_stratified_1000(val_dir, target_total=1000, seed=42)

    # 2. 本地 ConvNeXt 推論 (批量加速快篩)
    print("\n⏳ [階段 1/2] 正在進行本地 ConvNeXt GPU 全量推論與空間幾何分析...")
    local_records = []
    t0_local = time.perf_counter()

    for idx, s in enumerate(samples, 1):
        img_path = s["path"]
        try:
            img = Image.open(img_path).convert("RGB")
            tensor = _transform(img).unsqueeze(0).to(device)
            with torch.no_grad():
                probs, cos_sims = extract_features_and_similarities(model, tensor)
                raw_feats = model.forward_features(tensor) if hasattr(model, "forward_features") else None
            
            top_prob, top_idx = torch.max(probs, dim=0)
            score = float(top_prob.item())
            cos_s = float(cos_sims[top_idx].item()) if cos_sims is not None else 1.0
            pred_lbl = idx_mapping.get(int(top_idx.item()), "")
            pred_crop, pred_status, _ = parse_convnext_prediction(pred_lbl)

            # CAM 前景檢驗
            cam_ratio = compute_cam_foreground_alignment(model, raw_feats, int(top_idx.item()), img) if raw_feats is not None else 1.0
            
            # 部位感知檢驗
            fruit_mismatch = is_likely_fruit_for_leaf_disease(img, pred_lbl)

            # 判定本地預測是否正確
            match_crop = is_match(s["expected_crop"], pred_crop, SYNONYMS)
            match_status = is_match(s["expected_status"], pred_status, SYNONYMS)
            local_correct = match_crop and match_status

            # --- 判斷兩種邏輯之分流 ---
            # 舊版邏輯：僅看 Softmax 信心度 >= 0.70
            old_logic_hit = (score >= 0.70)
            
            # 現行生產版本邏輯 (三重幾何與空間防線)：
            # 1. 壓倒性置信度 (>= 0.85)
            # 2. 餘弦特徵幾何對齊 (>= 0.68)
            # 3. CAM 前景對齊 (>= 0.35)
            # 4. 部位不排斥
            current_logic_hit = (
                score >= settings.CONVNEXT_OVERWHELMING_CONFIDENCE
                and cos_s >= settings.CONVNEXT_MIN_COSINE_SIMILARITY
                and cam_ratio >= settings.CONVNEXT_MIN_CAM_FOREGROUND_RATIO
                and not fruit_mismatch
            )

            local_records.append({
                "sample_index": idx,
                "image": img_path.name,
                "folder": s["folder"],
                "expected_crop": s["expected_crop"],
                "expected_status": s["expected_status"],
                "expected_pv": s["expected_pv"],
                "local_pred_crop": pred_crop,
                "local_pred_status": pred_status,
                "local_score": round(score, 4),
                "local_cos_sim": round(cos_s, 4),
                "cam_ratio": round(cam_ratio, 4),
                "local_correct": local_correct,
                "old_logic_hit": old_logic_hit,
                "current_logic_hit": current_logic_hit,
            })
        except Exception as e:
            print(f"⚠️ 樣本 {img_path.name} 推論失敗: {e}")
            local_records.append({
                "sample_index": idx,
                "image": img_path.name,
                "folder": s["folder"],
                "expected_crop": s["expected_crop"],
                "expected_status": s["expected_status"],
                "expected_pv": s["expected_pv"],
                "local_pred_crop": "錯誤",
                "local_pred_status": "錯誤",
                "local_score": 0.0,
                "local_cos_sim": 0.0,
                "cam_ratio": 0.0,
                "local_correct": False,
                "old_logic_hit": False,
                "current_logic_hit": False,
            })

        if idx % 100 == 0:
            print(f"   [Phase 1 GPU 快篩進度] 已完成 {idx}/{len(samples)} 張分析 (累計耗時 {time.perf_counter() - t0_local:.1f}s)...")

    t_local_total = time.perf_counter() - t0_local
    print(f"✅ 本地推論完成！總耗時: {t_local_total:.2f}s (平均每張 {t_local_total/len(samples)*1000:.2f}ms)")

    # 存檔本地記錄
    local_cache_path = Path("artifacts/true_random_1000_local_records.json")
    with open(local_cache_path, "w", encoding="utf-8") as f:
        json.dump(local_records, f, ensure_ascii=False, indent=2)

    # 統計本地初步數據
    total_count = len(local_records)
    pure_local_acc = sum(r["local_correct"] for r in local_records) / total_count * 100
    old_hits = sum(r["old_logic_hit"] for r in local_records)
    cur_hits = sum(r["current_logic_hit"] for r in local_records)

    print("\n" + "=" * 65)
    print(f"📊【階段 1 本地分析：舊版邏輯 vs 現行生產邏輯（全品類 1,000 張盲測）】")
    print("=" * 65)
    print(f"1. 純本地模型單獨準確率 : {pure_local_acc:.2f}% ({sum(r['local_correct'] for r in local_records)}/{total_count})")
    print(f"2. 舊版邏輯快篩攔截率 (API 節省率): {old_hits/total_count*100:.2f}% ({old_hits}/{total_count}) [僅看 Softmax >= 0.70]")
    print(f"3. 現行版本快篩攔截率 (API 節省率): {cur_hits/total_count*100:.2f}% ({cur_hits}/{total_count}) [雙幾何防線 + CAM]")
    print(f"   ➔ 現行版本主動退避轉交雲端之困難/未知樣本: {total_count - cur_hits} 張 ({(total_count - cur_hits)/total_count*100:.2f}%)")
    print("=" * 65)

    # 3. 雲端 Gemini 兜底推論 (僅針對現行版本需要轉交的樣本，或兩者聯集)
    # 為了讓舊版與現行版都能完整評估，我們針對所有未命中的樣本進行 Gemini 推論
    needed_fallback_indices = [
        r["sample_index"] for r in local_records if (not r["current_logic_hit"] or not r["old_logic_hit"])
    ]
    print(f"\n⏳ [階段 2/2] 正在對 {len(needed_fallback_indices)} 張邊界/未知樣本執行 Gemini 3.8 Flash 兜底推論...")

    key_manager = KeyPoolManager(FREE_KEY_POOL)
    ckpt_path = Path("artifacts/true_random_1000_checkpoint.json")
    gemini_results = {}

    if ckpt_path.exists():
        try:
            with open(ckpt_path, "r", encoding="utf-8") as f:
                saved = json.load(f)
                gemini_results = saved.get("gemini_cache", {})
                print(f"🔄 偵測到中斷進度存檔，已成功載入 {len(gemini_results)} 筆已完成的 Gemini 結果！")
        except Exception:
            pass

    t_gemini_start = time.perf_counter()
    api_calls_made = 0

    for idx_num in needed_fallback_indices:
        r = local_records[idx_num - 1]
        img_name = r["image"]
        
        if img_name in gemini_results:
            continue

        sample_obj = samples[idx_num - 1]
        img_path = sample_obj["path"]

        # 呼叫 Gemini
        success = False
        for attempt in range(len(key_manager.keys) * 2):
            client, key_idx, key_tag = key_manager.get_client()
            try:
                img_pil = Image.open(img_path).convert("RGB")
                resp = client.models.generate_content(
                    model="gemini-3.8-flash",
                    contents=[img_pil, GEMINI_PROMPT_TEXT],
                )
                parsed = parse_gemini_response(resp.text)
                
                # 判定 Gemini 是否正確
                match_crop = is_match(r["expected_crop"], parsed["crop_name"], SYNONYMS)
                match_status = is_match(r["expected_status"], parsed["status_name"], SYNONYMS)
                gemini_correct = match_crop and match_status

                gemini_results[img_name] = {
                    "gemini_crop": parsed["crop_name"],
                    "gemini_status": parsed["status_name"],
                    "gemini_conf": parsed["confidence"],
                    "gemini_correct": gemini_correct,
                }
                api_calls_made += 1
                success = True
                
                if api_calls_made % 10 == 0:
                    print(f"   [進度 {len(gemini_results)}/{len(needed_fallback_indices)}] 金鑰 #{key_idx+1} 完成，API累計調用: {api_calls_made}")
                    # 存檔 checkpoint
                    with open(ckpt_path, "w", encoding="utf-8") as f:
                        json.dump({"gemini_cache": gemini_results}, f, ensure_ascii=False)
                
                time.sleep(delay_seconds)
                break
            except Exception as exc:
                err_str = str(exc)
                if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                    print(f"⚠️ 金鑰 #{key_idx+1} 觸發頻率限制 (429)，立即自動輪替下一組金鑰...")
                    key_manager.rotate_next()
                    time.sleep(2.0)
                else:
                    print(f"⚠️ 調用異常 ({err_str[:60]})... 輪替重試")
                    key_manager.rotate_next()
                    time.sleep(1.5)

        if not success:
            gemini_results[img_name] = {
                "gemini_crop": "失敗",
                "gemini_status": "失敗",
                "gemini_conf": 0.0,
                "gemini_correct": False,
            }

    # 最終存檔 checkpoint
    with open(ckpt_path, "w", encoding="utf-8") as f:
        json.dump({"gemini_cache": gemini_results}, f, ensure_ascii=False)

    # 4. 綜合統計分析 (現行版本 vs 舊版邏輯)
    print("\n🏆【全量 1,000 張隨機盲測大對決：現行版本 vs 舊版邏輯】")
    
    # 計算現行版本數據
    cur_final_correct = 0
    cur_rescued = 0
    cur_corrupted = 0
    cur_api_calls = 0

    # 計算舊版邏輯數據
    old_final_correct = 0
    old_rescued = 0
    old_corrupted = 0
    old_api_calls = 0

    full_details = []

    for r in local_records:
        img_name = r["image"]
        gem_info = gemini_results.get(img_name, {"gemini_correct": False, "gemini_crop": "", "gemini_status": ""})
        
        # 現行版本路線判定
        if r["current_logic_hit"]:
            cur_route = "本地快篩 (無呼叫API)"
            cur_correct = r["local_correct"]
            cur_final_crop = r["local_pred_crop"]
            cur_final_status = r["local_pred_status"]
        else:
            cur_route = "雲端Gemini兜底"
            cur_api_calls += 1
            cur_correct = gem_info["gemini_correct"]
            cur_final_crop = gem_info["gemini_crop"]
            cur_final_status = gem_info["gemini_status"]
            if not r["local_correct"] and cur_correct:
                cur_rescued += 1
            elif r["local_correct"] and not cur_correct:
                cur_corrupted += 1

        if cur_correct:
            cur_final_correct += 1

        # 舊版邏輯路線判定
        if r["old_logic_hit"]:
            old_route = "本地快篩 (舊版Softmax)"
            old_correct = r["local_correct"]
        else:
            old_route = "雲端Gemini兜底"
            old_api_calls += 1
            old_correct = gem_info["gemini_correct"]
            if not r["local_correct"] and old_correct:
                old_rescued += 1
            elif r["local_correct"] and not old_correct:
                old_corrupted += 1

        if old_correct:
            old_final_correct += 1

        full_details.append({
            **r,
            "gemini_crop": gem_info.get("gemini_crop", ""),
            "gemini_status": gem_info.get("gemini_status", ""),
            "gemini_correct": gem_info.get("gemini_correct", False),
            "current_route": cur_route,
            "current_correct": cur_correct,
            "old_route": old_route,
            "old_correct": old_correct,
        })

    cur_acc = cur_final_correct / total_count * 100
    old_acc = old_final_correct / total_count * 100
    cur_saved_pct = (total_count - cur_api_calls) / total_count * 100
    old_saved_pct = (total_count - old_api_calls) / total_count * 100

    report = {
        "title": "AI Challenger 61 類全品種真隨機 1,000 張盲測評估報告",
        "total_samples": total_count,
        "pure_local_accuracy": round(pure_local_acc, 2),
        "current_version": {
            "cascade_accuracy": round(cur_acc, 2),
            "api_saved_percentage": round(cur_saved_pct, 2),
            "total_api_calls": cur_api_calls,
            "gemini_rescued": cur_rescued,
            "gemini_corrupted": cur_corrupted,
            "net_contribution": cur_rescued - cur_corrupted,
        },
        "old_logic_comparison": {
            "cascade_accuracy": round(old_acc, 2),
            "api_saved_percentage": round(old_saved_pct, 2),
            "total_api_calls": old_api_calls,
            "gemini_rescued": old_rescued,
            "gemini_corrupted": old_corrupted,
            "net_contribution": old_rescued - old_corrupted,
        },
        "details": full_details,
    }

    report_path = Path("artifacts/ai_challenger_true_random_1000_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\n🎉 評測報告已成功產出: {report_path}")

    print("\n" + "=" * 65)
    print(f"📊【全量隨機 1,000 張盲測終極成績單】")
    print("=" * 65)
    print(f"🔹 純本地 ConvNeXt 單獨準確率 : {pure_local_acc:.2f}%")
    print(f"-----------------------------------------------------------------")
    print(f"🔹 【舊版邏輯 (單一Softmax)】 : 準確率 {old_acc:.2f}% | API 節省率 {old_saved_pct:.2f}% (調用 {old_api_calls} 次)")
    print(f"🔹 【現行版本 (三層級聯矩陣)】: 準確率 {cur_acc:.2f}% | API 節省率 {cur_saved_pct:.2f}% (調用 {cur_api_calls} 次)")
    print(f"-----------------------------------------------------------------")
    print(f"🌟 正向救援題數: +{cur_rescued} 題 | 淨貢獻: +{cur_rescued - cur_corrupted} 題")
    print("=" * 65)


if __name__ == "__main__":
    val_directory = Path(r"C:\Users\User\Downloads\val")
    run_benchmark(val_directory, delay_seconds=0.8)
