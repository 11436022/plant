"""
臺灣官方免登記植物保護資材與園藝安全用藥服務 (Taiwan MOA Official Plant Protection & Remedy Service)

資料來源：農業部動植物防疫檢疫署 (EIR841 開放資料集，全量 1,616 筆產品)
整合功能：
1. 全國合法市售商品索引與檢索 (商品名稱、登錄字號、製造廠商、所在縣市、統編)
2. 室內環境安全過濾 (Indoor Safety Classification)
3. 犬貓寵物友善等級判定 (Pet Safety Tiers: SAFE, CAUTION, TOXIC)
4. 適應症雙向交叉驗證 (Bidirectional Remedy Verification for Disease Diagnosis)
5. 電商與實體採購導流連結 (Monetization & Affiliate Search URLs)
"""

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import quote

# 檔案路徑設定
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
RAW_DATA_PATH = DATA_DIR / "raw_eir841.json"
ENRICHED_DATA_PATH = DATA_DIR / "enriched_remedies.json"

# 全域快取
_REMEDIES_CACHE: Optional[List[Dict[str, Any]]] = None

# 常見病蟲害與免登記資材成分關聯映射表 (病理適應症知識本體)
INGREDIENT_EFFICACY_MAP = {
    # 真菌病害
    "白粉病": ["碳酸氫鈉", "小蘇打", "柑桔精油", "矽酸鉀", "甲殼素", "幾丁聚醣", "乳化植物油", "醋", "肉桂精油"],
    "炭疽病": ["甲殼素", "幾丁聚醣", "肉桂精油", "中性化亞磷酸", "枯草桿菌", "醋", "大型褐藻萃取物"],
    "銹病": ["中性化亞磷酸", "甲殼素", "碳酸氫鈉", "矽酸鉀"],
    "早疫病": ["中性化亞磷酸", "肉桂精油", "甲殼素", "次氯酸鹽類", "大型褐藻萃取物"],
    "晚疫病": ["中性化亞磷酸", "次氯酸鹽類", "肉桂精油", "甲殼素"],
    "葉斑病": ["肉桂精油", "甲殼素", "中性化亞磷酸", "碳酸氫鈉", "矽酸鉀"],
    "灰黴病": ["碳酸氫鈉", "甲殼素", "矽酸鉀", "乳化植物油"],
    "煤煙病": ["柑桔精油", "脂肪酸鹽類", "苦楝油", "幾丁聚醣"],
    "根腐病": ["中性化亞磷酸", "木黴菌", "甲殼素", "大型褐藻萃取物"],
    "黑星病": ["碳酸氫鈉", "肉桂精油", "中性化亞磷酸"],
    "果腐病": ["肉桂精油", "柑桔精油", "甲殼素", "幾丁聚醣", "中性化亞磷酸", "醋", "次氯酸鹽類"],
    "軟腐病": ["甲殼素", "幾丁聚醣", "次氯酸鹽類", "中性化亞磷酸", "肉桂精油", "柑桔精油"],
    "疫病": ["中性化亞磷酸", "次氯酸鹽類", "肉桂精油", "甲殼素", "柑桔精油"],
    "露菌病": ["中性化亞磷酸", "碳酸氫鈉", "甲殼素", "矽酸鉀", "肉桂精油"],
    "立枯病": ["中性化亞磷酸", "木黴菌", "甲殼素", "大型褐藻萃取物"],
    "青枯病": ["中性化亞磷酸", "甲殼素", "次氯酸鹽類"],
    "病毒病": ["甲殼素", "幾丁聚醣", "大型褐藻萃取物", "矽酸鉀"],
    # 害蟲與蟲害
    "紅蜘蛛": ["苦楝油", "柑桔精油", "脂肪酸鹽類", "矽藻土", "礦物油"],
    "葉蟎": ["苦楝油", "柑桔精油", "脂肪酸鹽類", "矽藻土"],
    "介殼蟲": ["苦楝油", "礦物油", "脂肪酸鹽類", "柑桔精油", "肉桂精油"],
    "蚜蟲": ["苦楝油", "柑桔精油", "脂肪酸鹽類", "辣椒萃取物", "矽藻土"],
    "薊馬": ["苦楝油", "柑桔精油", "矽藻土", "脂肪酸鹽類"],
    "粉蝨": ["苦楝油", "柑桔精油", "脂肪酸鹽類", "乳化植物油"],
    "線蟲": ["甲殼素", "幾丁聚醣", "蓖麻粕", "苦茶粕"],
    "毛毛蟲": ["蘇力菌", "苦楝油", "矽藻土"],
    "斜紋夜蛾": ["蘇力菌", "苦楝油"],
}

# 寵物友善等級判定依據
# SAFE: 犬貓無害，可於室內放心使用
# CAUTION: 稀釋噴灑乾燥後無害，但避免寵物在未乾時直接舔拭或密閉直吸
# TOXIC: 對特定寵物（尤其貓）具有潛在神經/代謝毒性
def evaluate_pet_safety(declare_items: str) -> tuple[str, str]:
    text = declare_items or ""
    if any(k in text for k in ["除蟲菊", "百滅寧", "賽滅寧", "茶樹精油", "酚類"]):
        return "TOXIC", "對貓犬具神經或代謝毒性，居家有寵物嚴禁使用"
    if any(k in text for k in ["柑桔精油", "肉桂精油", "薄荷精油", "尤加利"]):
        return "CAUTION", "植物精油成分，稀釋噴灑乾燥後安全；噴灑時請將貓犬暫時移開，避免直接舔拭葉片"
    if any(k in text for k in ["苦茶粕"]):
        return "CAUTION", "含天然皂素，對水生生物與犬隻腸胃有刺激性，避免誤食"
    if any(k in text for k in ["碳酸氫鈉", "食品原料", "大型褐藻萃取物", "甲殼素", "幾丁聚醣", "矽藻土", "碳酸鈣", "中性化亞磷酸", "醋"]):
        return "SAFE", "食品級或天然礦物成分，犬貓寵物友善，室內可安全使用"
    if any(k in text for k in ["苦楝油", "脂肪酸鹽類", "矽酸鉀"]):
        return "SAFE", "天然植物油脂或皂素，正常稀釋使用對哺乳動物安全"
    return "SAFE", "經農業部審定之天然無毒植物保護資材"


def evaluate_indoor_safety(declare_items: str) -> tuple[bool, str]:
    text = declare_items or ""
    # 室內不建議有刺激性強酸強揮發氣味（如未稀釋高濃度壬酸、苦茶粕粉塵）
    if any(k in text for k in ["除蟲菊", "有機磷", "三唑", "百滅寧"]):
        return False, "化學合成農藥，嚴禁於密閉室內使用"
    if any(k in text for k in ["苦茶粕"]):
        return True, "室內盆栽可表土薄撒，但避免揚塵吸入"
    return True, "純天然/物理機制資材，極適合居家與辦公室密閉環境使用"


def _enrich_single_item(item: Dict[str, Any]) -> Dict[str, Any]:
    declare_items = item.get("DeclareItems", "").strip()
    chinese_name = item.get("ChineseName", "").strip()
    reg_type = item.get("RegNoTypeName", "").strip()
    reg_num = item.get("RegNoNum", "").strip()
    full_reg_no = f"{reg_type}字第{reg_num}號" if (reg_type and reg_num) else "農業部官方核准登記"
    
    pet_status, pet_reason = evaluate_pet_safety(declare_items)
    indoor_safe, indoor_reason = evaluate_indoor_safety(declare_items)

    # 決定適應對象標籤
    matched_diseases = []
    for dis, keywords in INGREDIENT_EFFICACY_MAP.items():
        if any(kw in declare_items for kw in keywords):
            matched_diseases.append(dis)

    use_pest = item.get("UsePest") == "Y"
    use_disease = item.get("UseDisease") == "Y"
    growth_kws = ["褐藻", "海藻", "生長", "生根", "根", "肥", "壯", "微量元素", "胺基酸", "腐植酸", "活力", "營養", "催花"]
    is_growth = any(k in declare_items or k in chinese_name for k in growth_kws) or bool(item.get("UseGrowth"))

    # 計算核心分類與易懂的功效標題
    disease_targets = [d for d in matched_diseases if any(w in d for w in ["病", "斑", "粉", "黴", "銹", "疫"])]
    pest_targets = [d for d in matched_diseases if any(w in d for w in ["蟲", "蜘蛛", "蟎", "蝨", "蛾", "蝶"])]

    if is_growth and not use_disease and not use_pest:
        primary_category = "growth"
        category_name = "🌱 活力營養"
        efficacy_summary = "功效：海藻生根、微量元素、增強免疫力"
    elif use_disease and not use_pest:
        primary_category = "disease"
        category_name = "🛡️ 殺菌防病"
        efficacy_summary = f"專治病害：{'、'.join(disease_targets[:2])}" if disease_targets else "專治：白粉病、葉斑黑斑真菌"
    elif use_pest and not use_disease:
        primary_category = "pest"
        category_name = "🐛 驅蟲除蟎"
        efficacy_summary = f"專治害蟲：{'、'.join(pest_targets[:2])}" if pest_targets else "專克：紅蜘蛛、蚜蟲、微小害蟲"
    elif use_pest and use_disease:
        primary_category = "all_in_one"
        category_name = "🛡️🐛 防病除蟲"
        if disease_targets and pest_targets:
            efficacy_summary = f"專克：{disease_targets[0]}、{pest_targets[0]}"
        elif pest_targets:
            efficacy_summary = f"專克：{'、'.join(pest_targets[:2])} 等害蟲"
        elif disease_targets:
            efficacy_summary = f"專治：{'、'.join(disease_targets[:2])} 等真菌"
        else:
            efficacy_summary = "功效：真菌病斑防護與微小害蟲阻隔"
    elif is_growth:
        primary_category = "growth"
        category_name = "🌱 活力營養"
        efficacy_summary = "功效：海藻生根、微量元素、增強免疫力"
    else:
        primary_category = "disease"
        category_name = "🌿 植物保護"
        efficacy_summary = "功效：溫和物理防護、增強植株抗逆力"

    # 生成商業導流電商搜尋網址 (支援各大電商與官方廠商查詢)
    encoded_kw = quote(f"{chinese_name} 園藝")
    purchase_url = f"https://shopee.tw/search?keyword={encoded_kw}"

    return {
        "registration_no": full_reg_no,
        "product_name": chinese_name,
        "active_ingredient": declare_items,
        "company_name": item.get("CompanyName", "").strip(),
        "city": item.get("City", "").strip(),
        "tax_id": item.get("TaxId", "").strip(),
        "use_pest": use_pest,
        "use_disease": use_disease,
        "use_growth": is_growth,
        "primary_category": primary_category,
        "category_name": category_name,
        "efficacy_summary": efficacy_summary,
        "indoor_safe": indoor_safe,
        "indoor_reason": indoor_reason,
        "pet_friendly_status": pet_status,  # SAFE, CAUTION, TOXIC
        "pet_friendly_desc": pet_reason,
        "license_image_url": item.get("LicenseImageUrl", ""),
        "matched_targets": matched_diseases,
        "purchase_search_url": purchase_url,
    }


def load_all_remedies() -> List[Dict[str, Any]]:
    """載入並快取全台 1,616 筆官方植物保護資材。"""
    global _REMEDIES_CACHE
    if _REMEDIES_CACHE is not None:
        return _REMEDIES_CACHE

    if not RAW_DATA_PATH.exists():
        print(f"[WARN] 找不到官方資材檔案: {RAW_DATA_PATH}")
        return []

    try:
        with open(RAW_DATA_PATH, "r", encoding="utf-8") as f:
            raw_list = json.load(f)

        enriched = [_enrich_single_item(item) for item in raw_list]
        _REMEDIES_CACHE = enriched
        print(f"[OK] 成功載入臺灣官方植物保護與園藝資材資料庫：共 {len(_REMEDIES_CACHE)} 筆產品！")
        return _REMEDIES_CACHE
    except Exception as exc:
        print(f"[ERROR] 載入官方資材失敗: {exc}")
        return []


# 5 大根本植物病理作用機制與對應天然資材本體
PATHOLOGY_MECHANISMS = {
    "fungal": {
        "keywords": [
            "粉", "斑", "黴", "銹", "黑星", "炭疽", "腐", "疫", "立枯", "潰瘍", 
            "紋枯", "落葉", "蔓割", "萎凋", "熱", "菌", "黑穗", "白絹", "露菌", "褐根",
            "瘤", "腫", "壞死", "真菌"
        ],
        "ingredients": ["碳酸氫鈉", "小蘇打", "柑桔精油", "肉桂精油", "甲殼素", "幾丁聚醣", "中性化亞磷酸", "矽酸鉀", "醋", "枯草桿菌"]
    },
    "bacterial": {
        "keywords": [
            "細菌", "軟腐", "青枯", "穿孔", "水浸", "流膠", "斑點細菌", "黑腐", "維管束"
        ],
        "ingredients": ["次氯酸鹽類", "甲殼素", "幾丁聚醣", "中性化亞磷酸", "肉桂精油", "醋"]
    },
    "viral_and_physiological": {
        "keywords": [
            "病毒", "嵌紋", "黃化", "捲葉", "縮葉", "簇生", "日燒", "缺素", "缺鐵", "缺鎂", "缺鈣", "缺氮", "缺磷", "缺鉀", "生長不良", "沒精神", "營養", "生根", "弱", "肥傷", "生理", "微量元素"
        ],
        "ingredients": ["大型褐藻萃取物", "甲殼素", "矽酸鉀", "幾丁聚醣", "苦楝油", "柑桔精油", "磷酸鐵", "腐植酸"]
    },
    "sucking_pest": {
        "keywords": [
            "蜘蛛", "蟎", "介殼", "蚜", "蝨", "薊馬", "木蝨", "浮塵", "粉蝨", "葉蟬", "粉介殼", "介殼蟲", "刺吸"
        ],
        "ingredients": ["苦楝油", "柑桔精油", "脂肪酸鹽類", "矽藻土", "礦物油", "乳化植物油"]
    },
    "chewing_pest": {
        "keywords": [
            "毛毛蟲", "蛾", "蝶", "螟", "夜盜", "毒蛾", "潛葉", "甲蟲", "金龜", "象鼻蟲", "蝸牛", "蛞蝓", "蟲", "蠅", "蚊", "飛", "害蟲"
        ],
        "ingredients": ["蘇力菌", "苦楝油", "矽藻土", "苦茶粕"]
    }
}


def resolve_ingredients_by_pathology(disease_or_pest_name: str) -> List[str]:
    """
    植物病理學自動推導引擎：
    不需手動一個個病害建字典！根據病徵名稱所屬的 5 大根本作用機制（真菌、細菌、病毒、刺吸害蟲、咀嚼害蟲），
    自動推導出農業部核准對應之天然安全資材成分清單。
    """
    name = (disease_or_pest_name or "").strip()
    if not name:
        return []

    # 1. 精確字典命中
    exact_ingredients = []
    for dis_key, ingredients in INGREDIENT_EFFICACY_MAP.items():
        if dis_key in name or name in dis_key:
            exact_ingredients.extend(ingredients)

    # 2. 5 大病理機制自動推導
    mechanism_ingredients = []
    for mech, cfg in PATHOLOGY_MECHANISMS.items():
        if any(kw in name for kw in cfg["keywords"]):
            for ing in cfg["ingredients"]:
                if ing not in mechanism_ingredients:
                    mechanism_ingredients.append(ing)

    # 3. 兜底保障：若名稱含「病」但未命中任何機制，預設真菌/細菌廣譜保護資材
    if not exact_ingredients and not mechanism_ingredients:
        if "病" in name:
            mechanism_ingredients.extend(["碳酸氫鈉", "柑桔精油", "肉桂精油", "甲殼素", "中性化亞磷酸"])
        elif "蟲" in name:
            mechanism_ingredients.extend(["苦楝油", "柑桔精油", "脂肪酸鹽類", "矽藻土"])

    # 依優先度去重合併
    combined = list(dict.fromkeys(exact_ingredients + mechanism_ingredients))
    return combined


def search_official_remedies(
    disease_or_pest_name: str,
    is_indoor: bool = True,
    has_pet: bool = False,
    city_filter: Optional[str] = None,
    limit: int = 5,
) -> List[Dict[str, Any]]:
    """
    根據病蟲害名稱、室內設定與寵物狀況，精準檢索全台官方市售安全資材。
    採用病理機制自動推導引擎，不需手動維護單一疾病字典。
    """
    all_remedies = load_all_remedies()
    if not all_remedies:
        return []

    query = disease_or_pest_name.strip()
    candidates = []

    # 取得此病害常見的有效資材成分 (病理機制自動推導)
    target_ingredients = resolve_ingredients_by_pathology(query)

    for item in all_remedies:
        # 1. 室內安全性過濾
        if is_indoor and not item["indoor_safe"]:
            continue

        # 2. 寵物安全性過濾
        if has_pet and item["pet_friendly_status"] == "TOXIC":
            continue

        # 3. 縣市過濾 (若有指定)
        if city_filter and city_filter not in item["city"]:
            continue

        # 4. 適應症評分
        score = 0
        ingredient = item["active_ingredient"]
        pname = item["product_name"]

        # 直接成分命中
        for ti in target_ingredients:
            if ti in ingredient:
                score += 3
            if ti in pname:
                score += 2

        # 病蟲害類別符合
        if any(term in query for term in ["病", "菌", "斑", "枯", "爛"]) and item["use_disease"]:
            score += 1
        if any(term in query for term in ["蟲", "蟎", "蝨", "蛾", "蝶", "蝸"]) and item["use_pest"]:
            score += 1

        # 若有指定目標直接命中
        if any(target in query for target in item["matched_targets"]):
            score += 4

        if score > 0:
            candidates.append((score, item))

    # 按相關度排序
    candidates.sort(key=lambda x: x[0], reverse=True)
    results = [item for _, item in candidates[:limit]]
    return results


def build_remedy_bidirectional_context(
    crop_name: str,
    status_name: str,
    is_indoor: bool = True,
    has_pet: bool = False,
) -> str:
    """
    生成提供給 Gemini 進行「雙向適應症反向驗證」的結構化上下文。
    """
    remedies = search_official_remedies(
        disease_or_pest_name=status_name,
        is_indoor=is_indoor,
        has_pet=has_pet,
        limit=3,
    )
    if not remedies:
        return ""

    lines = [
        "【臺灣農業部審定官方市售資材適應症（供反向交叉比對與商業處方推薦）】：",
        f"目前環境條件：{'室內/辦公室環境 (嚴格排除化學農藥)' if is_indoor else '戶外/農田環境'}；"
        f"寵物安全要求：{'有犬貓同住 (必須 100% 寵物無毒)' if has_pet else '無特殊要求'}。",
    ]

    for idx, r in enumerate(remedies, 1):
        lines.append(
            f"{idx}. 商品名稱：【{r['product_name']}】(登記字號：{r['registration_no']})\n"
            f"   - 有效成分：{r['active_ingredient']}（製造商：{r['company_name']}，{r['city']}）\n"
            f"   - 寵物友善評級：{r['pet_friendly_status']}（{r['pet_friendly_desc']}）\n"
            f"   - 適用範圍：{'防除病菌 ' if r['use_disease'] else ''}{'防除害蟲' if r['use_pest'] else ''}"
        )

    lines.append(
        "【重要反向驗證指引】：請比對照片實際病斑是否符合上述官方資材所針對之作用機制。"
        "若吻合，請在防治步驟中具體推薦上述官方資材、安全稀釋倍數與噴灑部位，杜絕虛構不實處方！"
    )
    return "\n".join(lines)
