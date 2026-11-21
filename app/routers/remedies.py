"""
臺灣官方免登記植物保護資材與園藝藥劑型錄 API
提供前端 Android 瀏覽全台 1,616 筆合法資材、包裝圖片、適應症與安全等級
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Query
from app.services.remedies import load_all_remedies

router = APIRouter(prefix="/remedies", tags=["Remedies Catalog"])


SYMPTOM_EXPANSIONS = {
    "紅蜘蛛": ["紅蜘蛛", "葉蟎", "蜘蛛", "柑桔精油", "苦楝油"],
    "白粉病": ["白粉病", "白粉", "小蘇打", "碳酸氫鈉", "白斑"],
    "介殼蟲": ["介殼蟲", "白蟲", "軟介殼", "蚜蟲", "粉蝨", "苦楝油"],
    "葉斑": ["葉斑病", "黑斑", "炭疽病", "枯葉", "黃斑", "早疫病", "晚疫病"],
    "果腐": ["果腐病", "果腐", "軟腐", "炭疽病", "肉桂精油", "柑桔精油", "甲殼素", "中性化亞磷酸", "萬晶油", "自然靈"],
    "果腐病": ["果腐病", "果腐", "軟腐", "炭疽病", "肉桂精油", "柑桔精油", "甲殼素", "中性化亞磷酸", "萬晶油", "自然靈"],
    "缺鐵": ["缺鐵", "缺鐵症", "微量元素", "大型褐藻萃取物", "磷酸鐵", "營養缺乏", "黃化", "好園地", "海元素", "金猛大", "葉本淨"],
    "缺鐵症": ["缺鐵", "缺鐵症", "微量元素", "大型褐藻萃取物", "磷酸鐵", "營養缺乏", "黃化", "好園地", "海元素", "金猛大", "葉本淨"],
    "缺素": ["缺素", "微量元素", "大型褐藻萃取物", "生長", "營養", "好園地", "海元素"],
    "營養缺乏": ["營養缺乏", "微量元素", "大型褐藻萃取物", "生長", "好園地", "海元素"],
    "軟腐": ["軟腐病", "果腐病", "甲殼素", "次氯酸鹽類", "中性化亞磷酸"],
    "腐": ["果腐病", "根腐病", "軟腐病", "肉桂精油", "中性化亞磷酸", "甲殼素"],
    "疫病": ["疫病", "晚疫病", "早疫病", "中性化亞磷酸", "次氯酸鹽類", "肉桂精油"],
    "營養": ["大型褐藻", "海藻", "生長", "生根", "微量元素", "活力", "營養", "壯"],
    "長蟲": ["害蟲", "苦楝油", "柑桔精油", "蟲", "蟎", "蝨"],
    "發霉": ["真菌", "碳酸氫鈉", "甲殼素", "醋", "黴", "病", "果腐"],
}


@router.get("/")
def get_remedies(
    q: Optional[str] = Query(None, description="關鍵字搜尋（品名、主成分、廠商、病蟲害適應症）"),
    category: str = Query("all", description="分類篩選：all, disease (病害), pest (蟲害), growth (活力營養), pet_safe (寵物友善), indoor_safe (室內安全)"),
    city: Optional[str] = Query(None, description="縣市篩選（例如：臺北市、臺中市）"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> Dict[str, Any]:
    """檢索與分頁瀏覽臺灣官方 1,616 筆免登記植物保護資材圖鑑。"""
    all_items = load_all_remedies()
    filtered = all_items

    # 1. 智慧關鍵字過濾
    if q and q.strip():
        raw_kw = q.strip().lower()
        search_terms = [raw_kw]
        for sym_key, exp_list in SYMPTOM_EXPANSIONS.items():
            if sym_key in raw_kw or raw_kw in sym_key:
                search_terms.extend(exp_list)
        search_terms = list(set(search_terms))

        # 優先取得推薦演算法命中商品 (如：果腐病命中的自然靈、萬晶油等，保證處方與寶典 100% 對齊)
        from app.services.remedies import search_official_remedies
        recom_items = search_official_remedies(raw_kw, is_indoor=True, has_pet=False, limit=20)
        recom_reg_nos = set(r["registration_no"] for r in recom_items)

        matched_items = []
        for item in filtered:
            is_recom = item["registration_no"] in recom_reg_nos
            is_kw_match = any(
                term in item["product_name"].lower()
                or term in item["active_ingredient"].lower()
                or term in item["company_name"].lower()
                or term in item["registration_no"].lower()
                or term in item.get("efficacy_summary", "").lower()
                or term in item.get("category_name", "").lower()
                or any(term in t.lower() for t in item["matched_targets"])
                for term in search_terms
            )
            if is_recom or is_kw_match:
                # 推薦處方商品給予最高權重優先排在最前
                priority = 0 if is_recom else 1
                matched_items.append((priority, item))

        matched_items.sort(key=lambda x: x[0])
        filtered = [item for _, item in matched_items]

    # 2. 類別過濾
    cat = category.strip().lower()
    if cat == "disease":
        filtered = [item for item in filtered if item.get("use_disease")]
    elif cat == "pest":
        filtered = [item for item in filtered if item.get("use_pest")]
    elif cat == "growth":
        filtered = [item for item in filtered if item.get("use_growth")]
    elif cat == "pet_safe":
        filtered = [item for item in filtered if item.get("pet_friendly_status") == "SAFE"]
    elif cat == "indoor_safe":
        filtered = [item for item in filtered if item.get("indoor_safe")]

    # 3. 縣市過濾
    if city and city.strip():
        c_filter = city.strip()
        filtered = [item for item in filtered if c_filter in item.get("city", "")]

    total = len(filtered)
    paged_items = filtered[skip : skip + limit]

    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "items": paged_items,
    }


@router.get("/{reg_no_num}")
def get_remedy_by_reg_no(reg_no_num: str) -> Optional[Dict[str, Any]]:
    """根據字號號碼（例如：01312）或完整字號查詢單筆商品詳情。"""
    all_items = load_all_remedies()
    num = reg_no_num.strip()
    for item in all_items:
        if num in item["registration_no"] or num in item.get("product_name", ""):
            return item
    return None
