import json
import sys
import time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import timm
import torch
from PIL import Image
from torchvision import transforms

from app.services.convnext import load_class_index, _transform, PLANTVILLAGE_TO_CHINESE
from scripts.evaluate_ai_challenger import AIC_TO_PV

device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
print(f"Device: {device}")

idx_to_class = load_class_index()
class_to_idx = {v: int(k) for k, v in idx_to_class.items()}
num_classes = len(idx_to_class)

conv_model = timm.create_model("convnext_small", num_classes=num_classes, pretrained=False)
conv_model.load_state_dict(torch.load("convnext_plant_best.pth", map_location="cpu"))
conv_model.to(device)
conv_model.eval()

val_dir = Path(r"C:\Users\User\Downloads\val")

# 收集 400 張測試樣本 (平均從 55 類中抽取，確保每類均有代表性)
cases_by_folder = {}
for folder_str in sorted(AIC_TO_PV.keys(), key=lambda x: int(x)):
    folder_path = val_dir / folder_str
    if not folder_path.exists():
        continue
    pv_class = AIC_TO_PV[folder_str]
    chinese_info = PLANTVILLAGE_TO_CHINESE.get(pv_class, {})
    exp_crop = chinese_info.get("crop", pv_class.split("___")[0])
    exp_status = chinese_info.get("status", pv_class.split("___")[1])
    exp_idx = class_to_idx.get(pv_class)

    imgs = list(folder_path.glob("*.jpg")) + list(folder_path.glob("*.png"))
    cases_by_folder[folder_str] = {
        "pv": pv_class,
        "crop": exp_crop,
        "status": exp_status,
        "idx": exp_idx,
        "images": sorted(imgs)
    }

# 均勻抽取 400 張 (每類約 7~8 張)
selected_400 = []
img_idx = 0
while len(selected_400) < 400:
    added = False
    for f_str, info in cases_by_folder.items():
        if img_idx < len(info["images"]):
            selected_400.append({
                "path": str(info["images"][img_idx]),
                "folder": f_str,
                "expected_crop": info["crop"],
                "expected_status": info["status"],
                "expected_pv": info["pv"],
                "expected_idx": info["idx"]
            })
            added = True
            if len(selected_400) >= 400:
                break
    if not added:
        break
    img_idx += 1

print(f"Total selected: {len(selected_400)} images across {len(cases_by_folder)} classes.")

# 跑 ConvNeXt
conf_threshold = 0.70
local_correct = 0
fallback_needed = []

for i, case in enumerate(selected_400):
    img_pil = Image.open(case["path"]).convert("RGB")
    tensor = _transform(img_pil).unsqueeze(0).to(device)
    with torch.no_grad():
        outputs = conv_model(tensor)
        probs = torch.softmax(outputs, dim=1)
        conf, pred = probs.max(dim=1)
        conf = conf.item()
        pred = pred.item()
    
    is_corr = (pred == case["expected_idx"])
    if is_corr:
        local_correct += 1
    
    if conf < conf_threshold:
        fallback_needed.append((i, case, conf, pred, is_corr))

print(f"\nConvNeXt Standalone on 400 images: {local_correct}/400 ({local_correct/400*100:.2f}%)")
print(f"High confidence (>=0.70): {400 - len(fallback_needed)} images ({(400-len(fallback_needed))/400*100:.1f}%)")
print(f"Fallback triggers (<0.70): {len(fallback_needed)} images ({len(fallback_needed)/400*100:.1f}%)")
