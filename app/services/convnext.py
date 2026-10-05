import json
from pathlib import Path
from typing import Optional

from PIL import Image
import torch
from torchvision import transforms

from app.core.config import settings

_convnext_model = None
_idx_to_class = None
_model_load_attempted = False

# 植物影像標準預處理
_transform = transforms.Compose([
    transforms.Resize(256),
    transforms.CenterCrop(224),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
])

# PlantVillage 38 類別繁體中文與病害類型對照表
PLANTVILLAGE_TO_CHINESE = {
    "Apple___Apple_scab": {"crop": "蘋果", "status": "黑星病", "category": "disease"},
    "Apple___Black_rot": {"crop": "蘋果", "status": "黑腐病", "category": "disease"},
    "Apple___Cedar_apple_rust": {"crop": "蘋果", "status": "銹病", "category": "disease"},
    "Apple___healthy": {"crop": "蘋果", "status": "健康", "category": "healthy"},
    "Blueberry___healthy": {"crop": "藍莓", "status": "健康", "category": "healthy"},
    "Cherry_(including_sour)___Powdery_mildew": {"crop": "櫻桃", "status": "白粉病", "category": "disease"},
    "Cherry_(including_sour)___healthy": {"crop": "櫻桃", "status": "健康", "category": "healthy"},
    "Corn_(maize)___Cercospora_leaf_spot Gray_leaf_spot": {"crop": "玉米", "status": "灰斑病", "category": "disease"},
    "Corn_(maize)___Common_rust_": {"crop": "玉米", "status": "銹病", "category": "disease"},
    "Corn_(maize)___Northern_Leaf_Blight": {"crop": "玉米", "status": "煤紋病", "category": "disease"},
    "Corn_(maize)___healthy": {"crop": "玉米", "status": "健康", "category": "healthy"},
    "Grape___Black_rot": {"crop": "葡萄", "status": "黑腐病", "category": "disease"},
    "Grape___Esca_(Black_Measles)": {"crop": "葡萄", "status": "黑痘病", "category": "disease"},
    "Grape___Leaf_blight_(Isariopsis_Leaf_Spot)": {"crop": "葡萄", "status": "褐斑病", "category": "disease"},
    "Grape___healthy": {"crop": "葡萄", "status": "健康", "category": "healthy"},
    "Orange___Haunglongbing_(Citrus_greening)": {"crop": "柑橘", "status": "黃龍病", "category": "disease"},
    "Peach___Bacterial_spot": {"crop": "桃", "status": "細菌性穿孔病", "category": "disease"},
    "Peach___healthy": {"crop": "桃", "status": "健康", "category": "healthy"},
    "Pepper,_bell___Bacterial_spot": {"crop": "甜椒", "status": "細菌性斑點病", "category": "disease"},
    "Pepper,_bell___healthy": {"crop": "甜椒", "status": "健康", "category": "healthy"},
    "Potato___Early_blight": {"crop": "馬鈴薯", "status": "早疫病", "category": "disease"},
    "Potato___Late_blight": {"crop": "馬鈴薯", "status": "晚疫病", "category": "disease"},
    "Potato___healthy": {"crop": "馬鈴薯", "status": "健康", "category": "healthy"},
    "Raspberry___healthy": {"crop": "覆盆子", "status": "健康", "category": "healthy"},
    "Soybean___healthy": {"crop": "大豆", "status": "健康", "category": "healthy"},
    "Squash___Powdery_mildew": {"crop": "南瓜", "status": "白粉病", "category": "disease"},
    "Strawberry___Leaf_scorch": {"crop": "草莓", "status": "葉焦病", "category": "disease"},
    "Strawberry___healthy": {"crop": "草莓", "status": "健康", "category": "healthy"},
    "Tomato___Bacterial_spot": {"crop": "番茄", "status": "細菌性斑點病", "category": "disease"},
    "Tomato___Early_blight": {"crop": "番茄", "status": "早疫病", "category": "disease"},
    "Tomato___Late_blight": {"crop": "番茄", "status": "晚疫病", "category": "disease"},
    "Tomato___Leaf_Mold": {"crop": "番茄", "status": "葉黴病", "category": "disease"},
    "Tomato___Septoria_leaf_spot": {"crop": "番茄", "status": "斑枯病", "category": "disease"},
    "Tomato___Spider_mites Two-spotted_spider_mite": {"crop": "番茄", "status": "二點葉蟎", "category": "pest"},
    "Tomato___Target_Spot": {"crop": "番茄", "status": "靶斑病", "category": "disease"},
    "Tomato___Tomato_Yellow_Leaf_Curl_Virus": {"crop": "番茄", "status": "黃化捲葉病毒病", "category": "disease"},
    "Tomato___Tomato_mosaic_virus": {"crop": "番茄", "status": "嵌紋病毒病", "category": "disease"},
    "Tomato___healthy": {"crop": "番茄", "status": "健康", "category": "healthy"},
}


def load_class_index() -> dict[int, str]:
    """載入 index -> class_name 映射。"""
    global _idx_to_class
    if _idx_to_class is not None:
        return _idx_to_class

    idx_path = Path(settings.CONVNEXT_CLASS_INDEX_PATH)
    if not idx_path.is_absolute():
        idx_path = settings.BASE_DIR / idx_path

    if idx_path.exists():
        with open(idx_path, "r", encoding="utf-8") as f:
            raw = json.load(f)
            _idx_to_class = {int(k): v for k, v in raw.items()}
    else:
        _idx_to_class = {i: name for i, name in enumerate(PLANTVILLAGE_TO_CHINESE.keys())}
    return _idx_to_class


def get_convnext_model():
    """
    惰性加載 ConvNeXt-small 分類模型。
    """
    global _convnext_model, _model_load_attempted
    if _model_load_attempted:
        return _convnext_model

    _model_load_attempted = True
    model_path = Path(settings.CONVNEXT_MODEL_PATH)
    if not model_path.is_absolute():
        model_path = settings.BASE_DIR / model_path

    if not model_path.exists():
        print(f"ℹ️ 本地 ConvNeXt 權重檔案不存在 ({model_path})，跳過本地快篩。")
        return None

    try:
        import timm

        load_class_index()
        num_classes = len(_idx_to_class) if _idx_to_class else 38
        model = timm.create_model("convnext_small", num_classes=num_classes, pretrained=False)
        state_dict = torch.load(str(model_path), map_location="cpu")
        model.load_state_dict(state_dict)
        model.eval()
        _convnext_model = model
        print(f"✅ 本地 ConvNeXt 模型載入成功 ({model_path}, 類別數: {num_classes})")
        return _convnext_model
    except ImportError:
        print("ℹ️ 尚未安裝 timm 套件，跳過 ConvNeXt 快篩。")
        return None
    except Exception as exc:
        print(f"⚠️ 載入 ConvNeXt 模型失敗: {exc}")
        return None


def parse_convnext_prediction(label: str) -> tuple[str, str, str]:
    """解析 PlantVillage 標籤為 (繁體作物名, 繁體狀態名, 類別)。"""
    info = PLANTVILLAGE_TO_CHINESE.get(label)
    if info:
        return info["crop"], info["status"], info["category"]

    if "___" in label:
        parts = label.split("___", 1)
        crop = parts[0].replace("_", " ").strip()
        status = parts[1].replace("_", " ").strip()
        category = "healthy" if status.lower() == "healthy" else "disease"
        return crop, status, category
    return label, "無法判定", "unknown"


def match_crop_to_class(user_crop: str, class_label: str) -> bool:
    """判斷使用者輸入/選取的作物名稱是否與該類別吻合。"""
    c_info = PLANTVILLAGE_TO_CHINESE.get(class_label)
    if c_info and c_info["crop"] == user_crop:
        return True

    # 英文與前綴比對
    user_lower = user_crop.lower()
    raw_crop = class_label.split("___")[0].lower() if "___" in class_label else class_label.lower()
    return user_lower in raw_crop or raw_crop in user_lower


def predict_convnext_fast_screen(
    image_path: str,
    crop_name: Optional[str] = None,
    mock_result: Optional[dict] = None,
) -> Optional[dict]:
    """
    步驟 1：本地模型 (ConvNeXt) 優先快篩。
    - 若使用者選定作物：限定只在該作物的常見病害類別中進行比對。
    - 若使用者未選定（未知）：評估全體類別之 Top-1 預測。
    - 成功且置信度 >= 75% 則回傳快篩命中結果，否則回傳 None。
    """
    if mock_result is not None:
        return mock_result

    model = get_convnext_model()
    if model is None:
        return None

    try:
        idx_mapping = load_class_index()
        img = Image.open(image_path).convert("RGB")
        tensor = _transform(img).unsqueeze(0)

        with torch.no_grad():
            output = model(tensor)
            probs = torch.softmax(output, dim=1)[0]

        is_crop_specified = bool(
            crop_name and crop_name.strip() not in ["未知", "未知作物", "未知植物", "無法判定"]
        )

        if not is_crop_specified:
            # 🌟 未限定作物時：本地閉集模型（僅 14 種作物）無法進行開集植物品種辨識。
            # 必須交由 Gemini 多模態大模型進行全域開集辨識，避免將香蕉、檸檬等外來作物誤判為桃子或番茄。
            print("🔍 [步驟 1 ConvNeXt 快篩] 作物未指定 (未知)，為避免閉集誤判，安全交由步驟 2 Gemini 進行開集識別")
            return None

        clean_crop = crop_name.strip()
        # 檢查使用者指定之作物是否為本地 ConvNeXt 支援的作物
        is_supported = any(match_crop_to_class(clean_crop, label) for label in idx_mapping.values())
        if not is_supported:
            # 使用者指定之作物（如香蕉、檸檬、芭樂等）不在本地模型訓練集內，
            # 安全交棒給 Gemini 多模態進行專屬長尾診斷，絕不強行反轉覆蓋為桃子。
            print(f"🔍 [步驟 1 ConvNeXt 快篩] 指定作物【{clean_crop}】非本地模型訓練集 (38類)，安全交由步驟 2 Gemini 專屬診斷")
            return None

        # 1. 取得全體 38 類別中整體信心最高者 (Global Top-1)
        top_prob, top_idx = torch.max(probs, dim=0)
        global_best_score = float(top_prob.item())
        global_best_label = idx_mapping.get(int(top_idx.item()))

        best_score = 0.0
        best_label = None
        is_override = False
        final_crop = None

        user_crop_best_score = 0.0
        user_crop_best_label = None

        # 限定搜尋與使用者指定作物相符的標籤
        for idx, label in idx_mapping.items():
            if match_crop_to_class(clean_crop, label):
                score = float(probs[idx].item())
                if score > user_crop_best_score:
                    user_crop_best_score = score
                    user_crop_best_label = label

        # 情況 A：使用者指定的作物命中 (信心度 >= 0.75)
        if user_crop_best_label and user_crop_best_score >= settings.CONVNEXT_MIN_CONFIDENCE:
            best_score = user_crop_best_score
            best_label = user_crop_best_label
            final_crop = clean_crop

        # 情況 B：⚡ 壓倒性信心反轉機制 (Overwhelming Confidence Override)
        # 使用者指定作物信心度極低 (< 0.30)，但全局 Top-1 具有壓倒性信心 (>= 0.85)
        elif (
            global_best_label
            and global_best_score >= settings.CONVNEXT_OVERWHELMING_CONFIDENCE
            and user_crop_best_score < 0.30
            and not match_crop_to_class(clean_crop, global_best_label)
        ):
            best_score = global_best_score
            best_label = global_best_label
            parsed_c, parsed_s, _ = parse_convnext_prediction(global_best_label)
            final_crop = parsed_c
            is_override = True
            print(
                f"⚡ 本地 ConvNeXt 觸發壓倒性信心反轉：使用者選定【{clean_crop}】(信心度僅 {user_crop_best_score:.2f})，"
                f"模型對【{final_crop} - {parsed_s}】具備壓倒性信心 ({global_best_score:.2f})，自動校正！"
            )

        if best_label and best_score >= settings.CONVNEXT_MIN_CONFIDENCE:
            parsed_crop, parsed_status, category = parse_convnext_prediction(best_label)
            if final_crop is None:
                final_crop = parsed_crop
            print(f"🎯 本地 ConvNeXt 快篩命中: {final_crop} - {parsed_status} (信心度: {best_score:.4f}, 原標籤: {best_label})")
            return {
                "crop_name": final_crop,
                "status_name": parsed_status,
                "category": category,
                "confidence": best_score,
                "grounding_source": "local_convnext_fast_screen",
                "requires_review": False,
                "is_confidence_override": is_override,
            }
        else:
            evaluated_lbl = user_crop_best_label or "無相符標籤"
            print(f"🔍 [步驟 1 ConvNeXt 快篩未達門檻] 作物【{clean_crop}】最高匹配【{evaluated_lbl}】信心度僅 {user_crop_best_score:.2f} (< {settings.CONVNEXT_MIN_CONFIDENCE:.2f} 門檻)，交由步驟 2 兜底")
            return None

        return None
    except Exception as exc:
        print(f"⚠️ ConvNeXt 快篩推論異常: {exc}")
        return None

