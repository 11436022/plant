"""
PlantVillage 38 類別資料庫種子腳本
1. 補齊 '覆盆子' (Raspberry) 至 crop 資料表。
2. 預載 PlantVillage 所對應之 14 種作物病害與蟲害描述及處方至 disease 與 pests 資料表。
"""

import sys
from pathlib import Path

# 確保 Windows 終端輸出 utf-8 支援繁體中文與 emoji
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# 將專案根目錄加入路徑
BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from app.db import models
from app.db.session import SessionLocal

# --- 作物新增定義 ---
CROPS_TO_ENSURE = [
    {"name": "覆盆子", "name_en": "Raspberry"},
]

# --- 病害種子資料 ---
DISEASES_DATA = [
    # 蘋果 (Apple)
    {
        "crop": "蘋果",
        "disease_name": "黑星病 (Apple Scab)",
        "aliases": ["黑星病", "Apple Scab", "Apple___Apple_scab"],
        "description": "主要危害葉片和果實。葉面上出現淡黃褐色圓形斑點，後擴大並長出黑綠色至深褐色天鵝絨狀黴層，嚴重時果實龜裂畸形。",
        "treatment": "1. 秋冬季清除落葉與病果並集中燒毀。\n2. 早春萌芽前噴灑石硫合劑或波爾多液。\n3. 發病初期選用待克利或賽普護汰寧等登記藥劑進行防治。",
        "source": "PlantVillage",
    },
    {
        "crop": "蘋果",
        "disease_name": "黑腐病 (Black Rot)",
        "aliases": ["黑腐病", "Black Rot", "Apple___Black_rot"],
        "description": "侵害葉片、果實及枝幹。葉片形成「青蛙眼」狀同心輪紋病斑；果實形成暗褐色同心輪紋腐爛，其上密生小黑粒點。",
        "treatment": "1. 修剪枯病枝並塗抹傷口保護劑。\n2. 落花後及時清理病僵果。\n3. 噴灑貝芬替或待克利等保護性殺菌劑。",
        "source": "PlantVillage",
    },
    {
        "crop": "蘋果",
        "disease_name": "銹病 (Cedar Apple Rust)",
        "aliases": ["銹病", "雪松蘋果銹病", "Cedar Apple Rust", "Apple___Cedar_apple_rust"],
        "description": "葉片表面出現亮黃色至橘紅色圓形病斑，病斑周圍有紅暈；後期葉背隆起並產生毛狀銹孢子器，嚴重時提早落葉。",
        "treatment": "1. 果園周圍避免種植檜柏等轉主寄主。\n2. 於展葉期至落花後噴灑三泰芬或腈菌唑等三唑類殺菌劑。\n3. 及早摘除初發病葉。",
        "source": "PlantVillage",
    },
    # 櫻桃 (Cherry)
    {
        "crop": "櫻桃",
        "disease_name": "白粉病 (Powdery Mildew)",
        "aliases": ["白粉病", "Powdery Mildew", "Cherry_(including_sour)___Powdery_mildew"],
        "description": "嫩梢和葉片表面覆蓋一層白色粉狀黴層，受害葉片常捲曲、變厚且脆，嫩葉生長停滯，嚴重時提早落葉。",
        "treatment": "1. 剪除受害嚴重的發病嫩梢與老葉。\n2. 保持樹冠內部通風透光。\n3. 發病初期可噴施硫磺膠體劑、亞托敏或三泰芬可濕性粉劑。",
        "source": "PlantVillage",
    },
    # 玉米 (Corn)
    {
        "crop": "玉米",
        "disease_name": "灰斑病 (Gray Leaf Spot)",
        "aliases": ["灰斑病", "Gray Leaf Spot", "Corn_(maize)___Cercospora_leaf_spot Gray_leaf_spot"],
        "description": "葉片上出現長矩形暗褐色至灰色病斑，病斑邊緣受平行葉脈限制成筆直條紋狀，濕度高時病斑兩面密生灰色黴層。",
        "treatment": "1. 選用抗病品種並實行合理輪作。\n2. 收穫後徹底翻耕田土與清除病殘體。\n3. 發病初期噴施亞托敏、待克利或吡唑醚菌酯等殺菌劑。",
        "source": "PlantVillage",
    },
    {
        "crop": "玉米",
        "disease_name": "銹病 (Common Rust)",
        "aliases": ["銹病", "Common Rust", "Corn_(maize)___Common_rust_"],
        "description": "葉片兩面散生或聚生圓形至長橢圓形紅褐色或鐵銹色夏孢子堆，後期表皮破裂散出紅褐色粉末。",
        "treatment": "1. 發病初期及早噴灑三泰芬（粉銹寧）或戊唑醇等藥劑。\n2. 避免田間種植過密，加強通風降濕。\n3. 增施磷鉀肥，提升植株抗病力。",
        "source": "PlantVillage",
    },
    {
        "crop": "玉米",
        "disease_name": "煤紋病 (Northern Leaf Blight)",
        "aliases": ["煤紋病", "大斑病", "Northern Leaf Blight", "Corn_(maize)___Northern_Leaf_Blight"],
        "description": "葉片上出現大型梭形灰綠色至灰褐色斑塊，長度可達 5 至 10 公分，潮濕時病斑表面產生大量灰黑色黴狀物。",
        "treatment": "1. 選用抗病雜交品種。\n2. 及時摘除下部老葉病葉，減少初次侵染源。\n3. 發病初期以得克利、待克利或代森錳鋅噴霧防治。",
        "source": "PlantVillage",
    },
    # 葡萄 (Grape)
    {
        "crop": "葡萄",
        "disease_name": "黑腐病 (Black Rot)",
        "aliases": ["黑腐病", "Black Rot", "Grape___Black_rot"],
        "description": "葉片出現紅褐色圓形病斑，邊緣深褐色；果實受害先呈淡褐色軟腐，後迅速皺縮乾癟為堅硬黑褐色僵果，表面密生黑色小粒。",
        "treatment": "1. 冬季徹底清園，刮除老皮並清除僵果枯葉。\n2. 開花前後及幼果期噴灑多菌靈、待克利或波爾多液。\n3. 套袋保護果穗，避免雨水飛濺傳播。",
        "source": "PlantVillage",
    },
    {
        "crop": "葡萄",
        "disease_name": "黑痘病 (Black Measles / Esca)",
        "aliases": ["黑痘病", "虎斑病", "Esca", "Black Measles", "Grape___Esca_(Black_Measles)"],
        "description": "葉片葉脈間黃化並壞死，呈現典型「虎斑紋」；果實表面出現小黑點，隨後果面局部凹陷乾枯變硬。",
        "treatment": "1. 修剪時嚴禁帶菌工具，剪除病枝後立即塗抹殺菌保護劑。\n2. 萌芽前噴施石硫合劑清園。\n3. 改善土壤結構與排水，避免植株過度乾旱或積水應激。",
        "source": "PlantVillage",
    },
    {
        "crop": "葡萄",
        "disease_name": "褐斑病 (Leaf Blight)",
        "aliases": ["褐斑病", "Leaf Blight", "Grape___Leaf_blight_(Isariopsis_Leaf_Spot)"],
        "description": "葉片出現大小不一的多角形或近圓形紅褐色至暗褐色病斑，葉背病斑對應處可見黑褐色絲絨狀黴層，多自下部老葉開始。",
        "treatment": "1. 秋冬季清掃落葉並集中掩埋或燒毀。\n2. 生長期間及時綁蔓摘心，增強通風透光。\n3. 發病初期可選用待克利、撲滅寧或波爾多液進行防治。",
        "source": "PlantVillage",
    },
    # 柑橘 (Orange)
    {
        "crop": "柑橘",
        "disease_name": "黃龍病 (Citrus Greening)",
        "aliases": ["黃龍病", "Citrus Greening", "立枯病", "Orange___Haunglongbing_(Citrus_greening)"],
        "description": "典型症狀為葉片「斑駁黃化」、葉脈木栓化或黃化，新梢發黃直立；果實變小、不對稱畸形且轉色不均（紅鼻子果），味酸味苦。",
        "treatment": "1. 全面嚴格防治傳播媒介「柑橘木蝨」（使用益達胺或賽速安等藥劑）。\n2. 堅持種植無毒健康苗木。\n3. 田間一旦確認病株應立即整株挖除並石灰消毒，防範蔓延。",
        "source": "PlantVillage",
    },
    # 桃 (Peach)
    {
        "crop": "桃",
        "disease_name": "細菌性穿孔病 (Bacterial Spot)",
        "aliases": ["細菌性穿孔病", "Bacterial Spot", "Peach___Bacterial_spot"],
        "description": "葉片最初出現水浸狀小斑點，後擴大為圓形至多角形紫褐色至黑褐色斑點，周圍具黃綠色暈圈，後期病斑乾枯脫落形成穿孔。",
        "treatment": "1. 增施有機肥與鉀肥，增強樹勢。\n2. 發芽前噴灑波爾多液清園。\n3. 展葉後噴施農用鏈黴素、春雷黴素或氧氯化銅等銅製劑進行預防。",
        "source": "PlantVillage",
    },
    # 甜椒 (Pepper, bell)
    {
        "crop": "甜椒",
        "disease_name": "細菌性斑點病 (Bacterial Spot)",
        "aliases": ["細菌性斑點病", "Bacterial Spot", "Pepper,_bell___Bacterial_spot"],
        "description": "葉片產生水浸狀小斑點，漸擴大成黃褐色近圓形病斑，中心淡褐色，邊緣深褐色微隆起，嚴重時落葉嚴重；果實表面產生粗糙隆起潰瘍斑。",
        "treatment": "1. 實行 2-3 年輪作，播種前種子溫湯浸種消毒。\n2. 雨後注意排水，避免田間積水與高濕。\n3. 發病初期噴灑多寧、氫氧化銅或春雷黴素進行防治。",
        "source": "PlantVillage",
    },
    # 馬鈴薯 (Potato)
    {
        "crop": "馬鈴薯",
        "disease_name": "早疫病 (Early Blight)",
        "aliases": ["早疫病", "Early Blight", "Potato___Early_blight"],
        "description": "葉片出現深褐色圓形或橢圓形病斑，具明顯同心輪紋，潮濕時病斑上長出黑色黴層。多從植株下部老葉開始向上蔓延。",
        "treatment": "1. 增施鉀肥與有機肥，防止植株早衰。\n2. 發病初期選用待克利、撲滅寧或百菌清進行葉面噴霧。\n3. 及時摘除底部枯老黃葉。",
        "source": "PlantVillage",
    },
    {
        "crop": "馬鈴薯",
        "disease_name": "晚疫病 (Late Blight)",
        "aliases": ["晚疫病", "Late Blight", "Potato___Late_blight"],
        "description": "葉尖或葉緣出現水浸狀暗綠色病斑，邊緣不明顯，濕度大時病斑邊緣生出一圈稀疏白黴；塊莖受害呈褐色凹陷腐爛。",
        "treatment": "1. 嚴禁種植帶病種薯。\n2. 發現中心病株立即拔除。\n3. 流行前即早噴灑待克利、滅達樂、甲霜靈或波爾多液保護。",
        "source": "PlantVillage",
    },
    # 南瓜 (Squash)
    {
        "crop": "南瓜",
        "disease_name": "白粉病 (Powdery Mildew)",
        "aliases": ["白粉病", "Powdery Mildew", "Squash___Powdery_mildew"],
        "description": "初期葉面或葉背產生白色粉狀小黴斑，隨後蔓延覆蓋全葉，如撒上一層白粉，後期葉片黃化變脆、枯焦乾死。",
        "treatment": "1. 注意通風透光，避免氮肥過量。\n2. 發病初期可用亞托敏、待克利、三泰芬或硫磺水懸劑進行均勻噴霧。\n3. 採收後清除病株殘體。",
        "source": "PlantVillage",
    },
    # 草莓 (Strawberry)
    {
        "crop": "草莓",
        "disease_name": "葉焦病 (Leaf Scorch)",
        "aliases": ["葉焦病", "Leaf Scorch", "Strawberry___Leaf_scorch"],
        "description": "葉片表面散生無數紫褐色至紫紅色小圓斑，漸擴大融合成不規則暗紫色焦枯大斑，使整葉葉緣枯焦如火燒狀。",
        "treatment": "1. 及時摘除病老葉集中深埋銷毀。\n2. 採用滴灌方式澆水，切忌噴灌漫灌。\n3. 發病初期噴施待克利、撲滅寧或百菌清保護葉片。",
        "source": "PlantVillage",
    },
    # 番茄 (Tomato)
    {
        "crop": "番茄",
        "disease_name": "細菌性斑點病 (Bacterial Spot)",
        "aliases": ["細菌性斑點病", "Bacterial Spot", "Tomato___Bacterial_spot"],
        "description": "葉片出現水浸狀暗綠色小斑點，漸轉為黑褐色稍凹陷斑點，外圍有黃色暈圈；果實表面形成火山口狀微隆起小黑點。",
        "treatment": "1. 種子消毒處理。\n2. 發病初期噴灑氫氧化銅、鏈黴素或克無菌等銅製劑或抗生素。\n3. 避免在露水未乾前進行田間整枝作業。",
        "source": "PlantVillage",
    },
    {
        "crop": "番茄",
        "disease_name": "葉黴病 (Leaf Mold)",
        "aliases": ["葉黴病", "Leaf Mold", "Tomato___Leaf_Mold"],
        "description": "主要危害葉片，葉面初現不規則淡黃色褪綠斑，葉背相應部位長出初為白色、後漸轉為黃褐至黑褐色天鵝絨狀濃密黴層。",
        "treatment": "1. 加強溫室通風排濕，控制相對濕度在 80% 以下。\n2. 發病初期可選用多菌靈、亞托敏或待克利噴灑。\n3. 及時摘除病葉改善通風。",
        "source": "PlantVillage",
    },
    {
        "crop": "番茄",
        "disease_name": "斑枯病 (Septoria Leaf Spot)",
        "aliases": ["斑枯病", "Septoria Leaf Spot", "Tomato___Septoria_leaf_spot"],
        "description": "葉片產生直徑約 2-3 毫米小圓斑，邊緣暗褐色，中央灰白色凹陷，病斑上散生許多針頭大小黑色小粒點（分生孢子器）。",
        "treatment": "1. 輪作換茬，清除田間病殘體。\n2. 發病初期噴施百菌清、待克利或代森錳鋅。\n3. 適當提早整枝打杈，改善田間通風。",
        "source": "PlantVillage",
    },
    {
        "crop": "番茄",
        "disease_name": "靶斑病 (Target Spot)",
        "aliases": ["靶斑病", "Target Spot", "Tomato___Target_Spot"],
        "description": "葉片出現圓形至不規則褐色壞死斑，具明顯黃色暈圈與同心靶環狀紋路，病斑脆裂易脫落穿孔。",
        "treatment": "1. 注意田間排濕通風。\n2. 噴灑待克利、嘧菌酯或苯醚甲環唑進行保護與治療。\n3. 及時清除發病下位葉。",
        "source": "PlantVillage",
    },
    {
        "crop": "番茄",
        "disease_name": "黃化捲葉病毒病 (Tomato Yellow Leaf Curl Virus)",
        "aliases": ["黃化捲葉病毒病", "TYLCV", "Tomato Yellow Leaf Curl Virus", "Tomato___Tomato_Yellow_Leaf_Curl_Virus"],
        "description": "植株矮縮，上部葉片明顯縮小、向上捲曲、葉緣褪綠黃化變厚變脆，開花結果稀少，果實發育不良。",
        "treatment": "1. 嚴防主要傳播媒介「銀葉粉蝨」（使用防蟲網、黃板及專用藥劑防治）。\n2. 選用抗病毒病（TY）品種。\n3. 發病初期拔除重病株並帶離田區銷毀。",
        "source": "PlantVillage",
    },
    {
        "crop": "番茄",
        "disease_name": "嵌紋病毒病 (Tomato Mosaic Virus)",
        "aliases": ["嵌紋病毒病", "ToMV", "Tomato Mosaic Virus", "Tomato___Tomato_mosaic_virus"],
        "description": "葉片出現濃淡不均的黃綠相間斑駁或嵌紋，葉片凹凸不平、扭曲變形呈蕨葉狀，植株生長停滯。",
        "treatment": "1. 整枝抹芽前先消毒雙手與剪刀，避免汁液接觸傳染。\n2. 及時防除蚜蟲等刺吸式害蟲。\n3. 播種前磷酸三鈉溶液浸種消毒。",
        "source": "PlantVillage",
    },
]

# --- 蟲害種子資料 ---
PESTS_DATA = [
    {
        "crop": "番茄",
        "pest_name": "二點葉蟎 (Spider Mites)",
        "aliases": ["二點葉蟎", "紅蜘蛛", "葉蟎", "Spider Mites", "Tomato___Spider_mites Two-spotted_spider_mite"],
        "description": "成蟲和若蟲聚集在葉背吸取汁液，葉面呈現微細黃白色褪綠斑點，嚴重時葉片枯黃捲縮脫落，並於葉背與嫩芽吐絲結網。",
        "treatment": "1. 保持田間濕潤，乾旱有利其快速繁殖。\n2. 釋放捕食蟎等天敵生物防治。\n3. 發生初期選用阿維菌素、噠蟎靈或螺蟎酯等登記殺蟎劑進行全面噴霧。",
        "source": "PlantVillage",
    }
]


def seed_plantvillage_data():
    db = SessionLocal()
    print("🚀 開始執行 PlantVillage 資料庫同步補全...")

    # 1. 確保作物存在
    print("\n--- [步驟 1] 補全作物列表 (Crop) ---")
    for item in CROPS_TO_ENSURE:
        existing = db.query(models.Crop).filter(models.Crop.crop_name == item["name"]).first()
        if not existing:
            new_crop = models.Crop(crop_name=item["name"], crop_name_en=item["name_en"])
            db.add(new_crop)
            db.commit()
            db.refresh(new_crop)
            print(f"✨ 新增作物: {new_crop.crop_name} (ID: {new_crop.crop_id})")
        else:
            print(f"ℹ️ 作物已存在: {existing.crop_name} (ID: {existing.crop_id})")

    # 建立作物快取字典
    crop_cache = {c.crop_name: c.crop_id for c in db.query(models.Crop).all()}

    # 2. 補全病害資料 (Disease)
    print("\n--- [步驟 2] 補全病害知識庫 (Disease) ---")
    added_disease_count = 0
    updated_disease_count = 0
    skipped_disease_count = 0

    for d in DISEASES_DATA:
        crop_id = crop_cache.get(d["crop"])
        if not crop_id:
            print(f"⚠️ 找不到作物: {d['crop']}，略過病害: {d['disease_name']}")
            continue

        # 檢查該作物是否已有相同或別名的病害
        existing = None
        for alias in d["aliases"] + [d["disease_name"]]:
            found = db.query(models.Disease).filter(
                models.Disease.crop_id == crop_id,
                models.Disease.disease_name.like(f"%{alias}%")
            ).first()
            if found:
                existing = found
                break

        if not existing:
            new_disease = models.Disease(
                crop_id=crop_id,
                disease_name=d["disease_name"],
                description=d["description"],
                treatment=d["treatment"],
                source_name=d.get("source", "PlantVillage"),
            )
            db.add(new_disease)
            added_disease_count += 1
            print(f"🌱 新增病害: [{d['crop']}] {d['disease_name']}")
        else:
            # 若既有資料缺少描述或處方，則補全
            if not existing.description or not existing.treatment:
                existing.description = existing.description or d["description"]
                existing.treatment = existing.treatment or d["treatment"]
                updated_disease_count += 1
                print(f"🔄 補全病害處方: [{d['crop']}] {existing.disease_name}")
            else:
                skipped_disease_count += 1

    db.commit()

    # 3. 補全蟲害資料 (Pests)
    print("\n--- [步驟 3] 補全蟲害知識庫 (Pests) ---")
    added_pest_count = 0
    for p in PESTS_DATA:
        crop_id = crop_cache.get(p["crop"])
        if not crop_id:
            continue

        existing = None
        for alias in p["aliases"] + [p["pest_name"]]:
            found = db.query(models.Pest).filter(
                models.Pest.crop_id == crop_id,
                models.Pest.pest_name.like(f"%{alias}%")
            ).first()
            if found:
                existing = found
                break

        if not existing:
            new_pest = models.Pest(
                crop_id=crop_id,
                pest_name=p["pest_name"],
                description=p["description"],
                treatment=p["treatment"],
                source_name=p.get("source", "PlantVillage"),
            )
            db.add(new_pest)
            added_pest_count += 1
            print(f"🐛 新增蟲害: [{p['crop']}] {p['pest_name']}")
        else:
            print(f"ℹ️ 蟲害已存在: [{p['crop']}] {existing.pest_name}")

    db.commit()
    db.close()

    print("\n🎉 PlantVillage 種子資料庫更新完成！")
    print(f"- 新增病害: {added_disease_count} 筆")
    print(f"- 補全病害: {updated_disease_count} 筆")
    print(f"- 略過既有: {skipped_disease_count} 筆")
    print(f"- 新增蟲害: {added_pest_count} 筆")


if __name__ == "__main__":
    seed_plantvillage_data()
