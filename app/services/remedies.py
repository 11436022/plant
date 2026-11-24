"""
臺灣官方免登記植物保護資材與園藝安全用藥服務 (Taiwan MOA Official Plant Protection & Remedy Service)

資料來源：農業部動植物防疫檢疫署 (EIR841 開放資料集)
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

# 寵物友善等級判定依據（系統基於學術文獻成分特性之風險分類，非農業部官方安全認證）
# SAFE -> LOW_RISK: 犬貓環境接觸風險低
# CAUTION -> MODERATE_RISK: 植物精油/皂素，稀釋乾燥後安全；噴灑時避開寵物與避免舔拭
# TOXIC -> HIGH_RISK: 對特定寵物（尤其貓）具潛在神經/代謝刺激性
def evaluate_pet_safety(declare_items: str) -> tuple[str, str, str, str]:
    text = declare_items or ""
    disclaimer_suffix = "（系統環境風險提示，非官方認證）"
    if any(k in text for k in ["除蟲菊", "百滅寧", "賽滅寧", "茶樹精油", "酚類"]):
        return (
            "TOXIC",
            f"對貓犬具神經或代謝刺激風險，居家有寵物嚴禁使用{disclaimer_suffix}",
            "HIGH_RISK",
            f"【寵物環境警示】成分對特定貓犬具神經或代謝刺激風險，居家有寵物請避免接觸{disclaimer_suffix}",
        )
    if any(k in text for k in ["柑桔精油", "肉桂精油", "薄荷精油", "尤加利"]):
        return (
            "CAUTION",
            f"植物精油成分，稀釋噴灑乾燥後風險低；噴灑時請將貓犬暫移，避免直接舔拭葉片{disclaimer_suffix}",
            "MODERATE_RISK",
            f"【寵物接觸提示】精油成分稀釋乾燥後接觸風險低，噴灑時請將寵物暫時移開，避免直接舔拭{disclaimer_suffix}",
        )
    if any(k in text for k in ["苦茶粕"]):
        return (
            "CAUTION",
            f"含天然皂素，對水生生物與犬隻腸胃有刺激性，避免誤食{disclaimer_suffix}",
            "MODERATE_RISK",
            f"【寵物接觸提示】含天然皂素對寵物腸胃具刺激性，盆栽施用請避免毛孩誤食{disclaimer_suffix}",
        )
    if any(k in text for k in ["碳酸氫鈉", "食品原料", "大型褐藻萃取物", "甲殼素", "幾丁聚醣", "矽藻土", "碳酸鈣", "中性化亞磷酸", "醋"]):
        return (
            "SAFE",
            f"食品級或天然礦物成分，接觸風險低，室內施用請保持通風{disclaimer_suffix}",
            "LOW_RISK",
            f"【寵物接觸提示】食品級或天然礦物成分，接觸風險低{disclaimer_suffix}",
        )
    if any(k in text for k in ["苦楝油", "脂肪酸鹽類", "矽酸鉀"]):
        return (
            "SAFE",
            f"天然植物油脂或皂素，正常稀釋使用接觸風險低{disclaimer_suffix}",
            "LOW_RISK",
            f"【寵物接觸提示】天然油脂或皂素成分，正常稀釋使用接觸風險低{disclaimer_suffix}",
        )
    return (
        "SAFE",
        f"農業部登錄天然植物保護資材，接觸風險低{disclaimer_suffix}",
        "LOW_RISK",
        f"【寵物接觸提示】農業部登錄之天然資材，接觸風險低{disclaimer_suffix}",
    )


def evaluate_indoor_safety(declare_items: str) -> tuple[bool, str, str]:
    text = declare_items or ""
    if any(k in text for k in ["除蟲菊", "有機磷", "三唑", "百滅寧"]):
        return (
            False,
            "化學合成農藥或強揮發成分，嚴禁於密閉室內使用（系統風險評估）",
            "【室內使用警示】具刺激性或化學成分，嚴禁於密閉室內環境使用",
        )
    if any(k in text for k in ["苦茶粕"]):
        return (
            True,
            "室內盆栽可表土薄撒，但避免揚塵吸入（系統風險評估）",
            "【室內使用提示】微量表土覆蓋，避免揚塵吸入，保持環境通風",
        )
    return (
        True,
        "純天然/物理機制資材，施用後保持通風即可（系統風險評估）",
        "【室內使用提示】天然物理資材，施用後請置於通風採光處保持通氣",
    )


def _enrich_single_item(item: Dict[str, Any]) -> Dict[str, Any]:
    declare_items = item.get("DeclareItems", "").strip()
    chinese_name = item.get("ChineseName", "").strip()
    reg_type = item.get("RegNoTypeName", "").strip()
    reg_num = item.get("RegNoNum", "").strip()
    full_reg_no = f"{reg_type}字第{reg_num}號" if (reg_type and reg_num) else "農業部官方核准登記"
    
    pet_status, pet_reason, pet_risk_lvl, pet_risk_note = evaluate_pet_safety(declare_items)
    indoor_safe, indoor_reason, indoor_risk_note = evaluate_indoor_safety(declare_items)

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
        "indoor_risk_notice": indoor_risk_note,
        "pet_friendly_status": pet_status,  # SAFE, CAUTION, TOXIC
        "pet_friendly_desc": pet_reason,
        "pet_risk_level": pet_risk_lvl,
        "pet_risk_notice": pet_risk_note,
        "disclaimer": "本系統之環境與寵物注意事項係依成分學術特性提供之輔助風險提示，非農業部官方安全認證；使用倍數與範圍請以產品包裝正式標示為準。",
        "license_image_url": item.get("LicenseImageUrl", ""),
        "matched_targets": matched_diseases,
        "purchase_search_url": purchase_url,
    }


def load_all_remedies() -> List[Dict[str, Any]]:
    """載入並快取全台官方植物保護資材。"""
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


def verify_remedy_suitability(
    item: Dict[str, Any],
    disease_or_pest_name: str,
    target_ingredients: List[str],
) -> Dict[str, Any]:
    """
    第二層：官方資料依據與安全驗證模組 (Official Evidence & Safety Verification)
    
    評估項目拆分：
    1. pathology_score (病理機制相關分): 推導成分與產品成分/名稱的關聯度
    2. official_evidence_level (官方登記依據等級: HIGH, MEDIUM, LOW):
       - HIGH: 官方資料 UseDisease/UsePest 登記用途符合，且品名/成分明確命中適應機制
       - MEDIUM: 官方資料具備防除登記，成分符合病理機制
       - LOW: 僅為一般生長營養 (UseGrowth) 或無對應防除登記，不得宣稱病害防除特效
    3. verified: 是否通過官方依據門檻
    4. rejection_reason: 若被攔截或降級，說明原因（用於口試實驗二：不符合條件之資材攔截率）
    """
    query = (disease_or_pest_name or "").strip()
    is_disease_query = any(w in query for w in ["病", "菌", "斑", "枯", "爛", "黴", "粉", "銹", "腐", "疫"])
    is_pest_query = any(w in query for w in ["蟲", "蟎", "蝨", "蛾", "蝶", "蝸", "蜘蛛", "薊馬"])

    use_disease = item.get("use_disease", False)
    use_pest = item.get("use_pest", False)
    use_growth = item.get("use_growth", False)
    ingredient = item.get("active_ingredient", "")
    pname = item.get("product_name", "")

    # 1. 計算病理相關分 (Pathology Score)
    pathology_score = 0
    matched_ingr = [ti for ti in target_ingredients if ti in ingredient or ti in pname]
    if matched_ingr:
        pathology_score += len(matched_ingr) * 3

    if any(target in query for target in item.get("matched_targets", [])):
        pathology_score += 4

    # 2. 官方資料登錄依據查核 (Official Evidence Check)
    evidence_level = "LOW"
    evidence_notes = []
    rejection_reason = None
    is_verified = False

    if is_disease_query:
        if use_disease:
            if pathology_score >= 3:
                evidence_level = "HIGH"
                evidence_notes.append("符合農業部公告之病害防除登錄類別，且有效成分具明確病理機制支持")
                is_verified = True
            else:
                evidence_level = "MEDIUM"
                evidence_notes.append("符合農業部公告之病害防除登錄類別，成分具廣譜保護特性")
                is_verified = True
        elif use_growth and not use_disease:
            evidence_level = "LOW"
            rejection_reason = "官方登記用途為促進生長/活力營養，非病害防除資材，依據不足進行攔截降級"
            evidence_notes.append("注意：此產品官方登記為生長營養類，非直接病害防除資材")
        else:
            evidence_level = "LOW"
            rejection_reason = "官方登記未包含病害防除用途 (UseDisease!=Y)"
            evidence_notes.append("官方登錄資訊未包含病害防治依據")

    elif is_pest_query:
        if use_pest:
            if pathology_score >= 3:
                evidence_level = "HIGH"
                evidence_notes.append("符合農業部公告之害蟲防除登錄類別，且成分具明確驅蟲除蟎機制")
                is_verified = True
            else:
                evidence_level = "MEDIUM"
                evidence_notes.append("符合農業部公告之害蟲防除登錄類別")
                is_verified = True
        elif use_growth and not use_pest:
            evidence_level = "LOW"
            rejection_reason = "官方登記用途為促進生長，非蟲害防除資材，進行攔截降級"
            evidence_notes.append("注意：此產品官方登記為生長營養類，非蟲害防除資材")
        else:
            evidence_level = "LOW"
            rejection_reason = "官方登記未包含害蟲防除用途 (UsePest!=Y)"
            evidence_notes.append("官方登錄資訊未包含害蟲防治依據")

    else:
        # 一般性保護或未知分類
        if use_disease or use_pest:
            evidence_level = "MEDIUM"
            evidence_notes.append("具官方病蟲害防除登錄，請依產品標示之適應範圍施用")
            is_verified = True
        else:
            evidence_level = "LOW"
            evidence_notes.append("一般植物保護或營養資材")

    return {
        "verified": is_verified,
        "pathology_score": pathology_score,
        "official_evidence_level": evidence_level,
        "official_evidence_note": "；".join(evidence_notes),
        "rejection_reason": rejection_reason,
        "matched_mechanism_ingredients": matched_ingr,
    }


def search_official_remedies(
    disease_or_pest_name: str,
    is_indoor: bool = True,
    has_pet: bool = False,
    city_filter: Optional[str] = None,
    limit: int = 5,
    verified_only: bool = True,
) -> List[Dict[str, Any]]:
    """
    雙層驗證資材檢索服務：
    第一層：植物病理機制成分映射與初篩
    第二層：農業部官方登錄依據驗證 (UseDisease/UsePest)、寵物接觸風險與室內安全條件過濾
    """
    all_remedies = load_all_remedies()
    if not all_remedies:
        return []

    query = disease_or_pest_name.strip()
    candidates = []

    # 第一層：取得此病害常見的有效資材成分 (病理機制自動推導)
    target_ingredients = resolve_ingredients_by_pathology(query)

    for base_item in all_remedies:
        # 環境條件過濾
        if is_indoor and not base_item["indoor_safe"]:
            continue
        if has_pet and base_item["pet_friendly_status"] == "TOXIC":
            continue
        if city_filter and city_filter not in base_item["city"]:
            continue

        # 第二層：官方依據與適用性驗證
        verification = verify_remedy_suitability(base_item, query, target_ingredients)
        pathology_score = verification["pathology_score"]

        # 若要求僅推薦有官方依據驗證通過者，且該產品未通過驗證 (例如純營養品被拿來當病害藥)，進行攔截
        if verified_only and not verification["verified"]:
            continue

        if pathology_score <= 0 and not any(term in query for term in ["病", "菌", "斑", "蟲", "蟎"]):
            continue

        # 計算綜合排序權重：官方依據等級權重 + 病理機制吻合分
        evidence_weight = 10 if verification["official_evidence_level"] == "HIGH" else (5 if verification["official_evidence_level"] == "MEDIUM" else 0)
        total_score = evidence_weight + pathology_score

        # 封裝包含驗證資訊的資材字典
        enriched_item = dict(base_item)
        enriched_item.update({
            "verified": verification["verified"],
            "official_evidence_level": verification["official_evidence_level"],
            "official_evidence_note": verification["official_evidence_note"],
            "pathology_score": pathology_score,
            "total_score": total_score,
            "rejection_reason": verification["rejection_reason"],
        })

        candidates.append((total_score, enriched_item))

    # 按綜合分數排序 (官方依據高 + 機制高度吻合者居前)
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
        verified_only=True,
    )
    if not remedies:
        return ""

    lines = [
        "【臺灣農業部登錄官方市售資材（經系統雙層病理與依據驗證）】：",
        f"環境條件需求：{'室內/辦公室盆栽環境' if is_indoor else '戶外/農田環境'}；"
        f"寵物接觸考量：{'有犬貓同住 (需低風險資材)' if has_pet else '無特殊要求'}。",
    ]

    for idx, r in enumerate(remedies, 1):
        lines.append(
            f"{idx}. 商品名稱：【{r['product_name']}】(登錄字號：{r['registration_no']})\n"
            f"   - 有效成分：{r['active_ingredient']}（製造商：{r['company_name']}，{r['city']}）\n"
            f"   - 官方依據等級：{r.get('official_evidence_level', 'MEDIUM')}（{r.get('official_evidence_note', '')}）\n"
            f"   - 寵物接觸風險提示：{r.get('pet_risk_notice', r.get('pet_friendly_desc', ''))}\n"
            f"   - 適用範圍：{'防除病菌 ' if r['use_disease'] else ''}{'防除害蟲' if r['use_pest'] else ''}"
        )

    lines.append(
        "【重要安全防護與規範指引】：\n"
        "1. 請比對照片病斑特徵是否符合上述官方資材之作用機制。\n"
        "2. 嚴禁自行虛構特定稀釋倍數或未經驗證的寶特瓶調配公式！\n"
        "3. 處方指引中請明確提示使用者『嚴格參照產品外包裝標示之官方稀釋倍數施用』，並先局部試噴以杜絕藥傷。"
    )
    return "\n".join(lines)
