"""
真實田間遷移微調對照實驗 (Empirical Field Domain Adaptation Experiment)
回答核心學術問題：「如果所有模型都一起套上田間自然環境照片 (PlantVillage + Field Images) 進行微調，實測數據到底是多少？」

實驗設計：
1. 資料來源：AI Challenger 2018 (4,520 張真實農田田間照片，含烈日反光、泥土背景、多重重疊)
2. 資料切分 (Seed=42 嚴格隨機分層)：
   - 50% (2,260 張) 作為田間訓練集 (用於各模型遷移微調)
   - 50% (2,260 張) 作為全新獨立測試集 (任何模型訓練時皆完全不可見)
3. 評測對象：
   - ConvNeXt-Small (本專案核心)
   - ResNet-50 (經典標竿)
   - EfficientNet-B0 (複合縮放)
   - MobileNetV3-Large (邊緣輕量)
4. 對比指標：
   - 未看過田間前 (純 PlantVillage 權重) 之測試集準確率
   - 看過田間微調後 (PlantVillage + Field 微調權重) 之測試集準確率
   - 遷移適應增益 (Domain Adaptation Gain, Δ)
"""

import functools
import gc
import json
import os
import random
import sys
import time
from pathlib import Path

# 強制啟用即時 flush
print = functools.partial(print, flush=True)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import timm
import torch
import torch.nn as nn
from PIL import Image
from torch.amp import GradScaler, autocast
from torch.utils.data import DataLoader, Dataset
from torchvision import transforms

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.services.convnext import load_class_index
from scripts.evaluate_ai_challenger import AIC_TO_PV

plt.rcParams["font.sans-serif"] = ["Microsoft JhengHei", "DejaVu Sans", "Arial"]
plt.rcParams["axes.unicode_minus"] = False
matplotlib.rcParams["figure.dpi"] = 300

ROOT_DIR = Path(__file__).resolve().parents[1]
ARTIFACTS_DIR = ROOT_DIR / "artifacts"
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
VAL_DIR = Path(r"C:\Users\User\Downloads\val")

SEED = 42
random.seed(SEED)
np.random.seed(SEED)
torch.manual_seed(SEED)
if torch.cuda.is_available():
    torch.cuda.manual_seed_all(SEED)


class FieldDataset(Dataset):
    def __init__(self, samples: list[tuple[str, int]], transform=None):
        self.samples = samples
        self.transform = transform

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        path_str, label = self.samples[idx]
        try:
            img = Image.open(path_str).convert("RGB")
        except Exception:
            img = Image.new("RGB", (224, 224), (0, 0, 0))
        if self.transform:
            img = self.transform(img)
        return img, label


MODELS = [
    {
        "id": "convnext_small",
        "name": "ConvNeXt-Small",
        "timm_name": "convnext_small",
        "pth": "artifacts/empirical_convnext_small_plantvillage.pth",
        "batch_size": 32,
        "color": "#1B5E20",
    },
    {
        "id": "resnet50",
        "name": "ResNet-50",
        "timm_name": "resnet50",
        "pth": "artifacts/empirical_resnet50_plantvillage.pth",
        "batch_size": 64,
        "color": "#1565C0",
    },
    {
        "id": "efficientnet_b0",
        "name": "EfficientNet-B0",
        "timm_name": "efficientnet_b0",
        "pth": "artifacts/empirical_efficientnet_b0_plantvillage.pth",
        "batch_size": 64,
        "color": "#E65100",
    },
    {
        "id": "mobilenetv3_large",
        "name": "MobileNetV3-Large",
        "timm_name": "mobilenetv3_large_100",
        "pth": "artifacts/empirical_mobilenetv3_large_plantvillage.pth",
        "batch_size": 64,
        "color": "#0277BD",
    },
]


def evaluate(model: nn.Module, loader: DataLoader, device: torch.device) -> tuple[float, int, int]:
    model.eval()
    correct = 0
    total = 0
    with torch.no_grad():
        for imgs, labels in loader:
            imgs, labels = imgs.to(device, non_blocking=True), labels.to(device, non_blocking=True)
            with autocast("cuda"):
                outputs = model(imgs)
            preds = outputs.argmax(dim=1)
            correct += (preds == labels).sum().item()
            total += labels.size(0)
    acc = (correct / total) * 100 if total > 0 else 0.0
    return round(acc, 2), correct, total


def run_experiment():
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    print(f"🚀 [啟動田間適應實測] 運算裝置: {device} ({torch.cuda.get_device_name(0)})")

    # 1. 建立影像清單
    idx_to_class = load_class_index()
    class_to_idx = {v: int(k) for k, v in idx_to_class.items()}

    all_samples = []
    for folder_str, pv_class in AIC_TO_PV.items():
        folder = VAL_DIR / folder_str
        if not folder.exists() or pv_class not in class_to_idx:
            continue
        idx = class_to_idx[pv_class]
        for ext in ("*.jpg", "*.jpeg", "*.png"):
            for p in folder.glob(ext):
                all_samples.append((str(p), idx))

    # 按類別分層隨機切分 50% 訓練 (2,260 張)、50% 測試 (2,260 張)
    by_class = {}
    for p, lbl in all_samples:
        by_class.setdefault(lbl, []).append((p, lbl))

    train_samples = []
    test_samples = []
    for lbl, items in by_class.items():
        random.seed(SEED + lbl)
        random.shuffle(items)
        split = len(items) // 2
        train_samples.extend(items[:split])
        test_samples.extend(items[split:])

    random.seed(SEED)
    random.shuffle(train_samples)
    random.shuffle(test_samples)

    print(f"📦 總田間樣本: {len(all_samples)} 張")
    print(f"📦 田間訓練集 (用於各模型遷移微調): {len(train_samples)} 張")
    print(f"📦 獨立測試集 (完全未見過的盲測集): {len(test_samples)} 張")

    train_trans = transforms.Compose([
        transforms.Resize(256),
        transforms.RandomCrop(224),
        transforms.RandomHorizontalFlip(),
        transforms.ColorJitter(brightness=0.1, contrast=0.1),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])
    test_trans = transforms.Compose([
        transforms.Resize(256),
        transforms.CenterCrop(224),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])

    train_ds = FieldDataset(train_samples, transform=train_trans)
    test_ds = FieldDataset(test_samples, transform=test_trans)
    test_loader = DataLoader(test_ds, batch_size=128, shuffle=False, num_workers=0, pin_memory=True)

    results = []

    for m_info in MODELS:
        m_name = m_info["name"]
        timm_name = m_info["timm_name"]
        pth_path = ROOT_DIR / m_info["pth"]
        batch_size = m_info["batch_size"]

        print(f"\n{'='*70}")
        print(f"🥊 正在測試模型: 【{m_name}】")
        print(f"{'='*70}")

        # 載入原始 PlantVillage 權重
        model = timm.create_model(timm_name, num_classes=38, pretrained=False)
        model.load_state_dict(torch.load(pth_path, map_location="cpu"))
        model.to(device)

        # 1. 測微調前 (純 PlantVillage 權重在 2,260 張未見田間測試集的表現)
        pre_acc, pre_corr, pre_tot = evaluate(model, test_loader, device)
        print(f"   📊 [微調前 (純白底)] 獨立田間測試集準確率: {pre_acc:.2f}% ({pre_corr}/{pre_tot})")

        # 2. 田間微調 2 輪 (給所有人吃一模一樣的田間訓練資料)
        train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True, num_workers=0, pin_memory=True)
        optimizer = torch.optim.AdamW(model.parameters(), lr=5e-5, weight_decay=1e-2)
        criterion = nn.CrossEntropyLoss()
        scaler = GradScaler("cuda")

        t0 = time.perf_counter()
        for epoch in range(1, 3):
            model.train()
            r_loss = 0.0
            r_corr = 0
            total_n = 0
            for imgs, lbls in train_loader:
                imgs, lbls = imgs.to(device, non_blocking=True), lbls.to(device, non_blocking=True)
                optimizer.zero_grad(set_to_none=True)
                with autocast("cuda"):
                    outputs = model(imgs)
                    loss = criterion(outputs, lbls)
                scaler.scale(loss).backward()
                scaler.step(optimizer)
                scaler.update()

                r_loss += loss.item() * imgs.size(0)
                preds = outputs.argmax(dim=1)
                r_corr += preds.eq(lbls).sum().item()
                total_n += lbls.size(0)

            print(f"      -> Epoch {epoch}/2 | Train Loss: {r_loss/total_n:.4f} | Train Acc: {r_corr/total_n*100:.2f}%")

        ft_time = time.perf_counter() - t0

        # 3. 測微調後 (套上田間訓練後，在同一批 2,260 張獨立盲測集的表現)
        post_acc, post_corr, post_tot = evaluate(model, test_loader, device)
        gain = round(post_acc - pre_acc, 2)
        print(f"   ⭐ [微調後 (白底+田間)] 獨立田間測試集準確率: {post_acc:.2f}% ({post_corr}/{post_tot})")
        print(f"   🎯 實戰遷移提升幅度 (Gain): +{gain:.2f}% (微調耗時: {ft_time:.1f}s)")

        # 存檔微調後權重
        save_ft_path = ARTIFACTS_DIR / f"field_adapted_{m_info['id']}.pth"
        torch.save(model.state_dict(), save_ft_path)

        results.append({
            "name": m_name,
            "id": m_info["id"],
            "color": m_info["color"],
            "pre_field_acc": pre_acc,
            "post_field_acc": post_acc,
            "gain": gain,
            "ft_time_sec": round(ft_time, 1),
        })

        del model, optimizer, scaler
        gc.collect()
        torch.cuda.empty_cache()

    # 4. 產出報告與圖表
    report_file = ARTIFACTS_DIR / "field_adaptation_experiment_report.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(
            {
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "total_field_samples": len(all_samples),
                "train_samples": len(train_samples),
                "test_samples": len(test_samples),
                "results": results,
            },
            f,
            ensure_ascii=False,
            indent=2,
        )
    print(f"\n📄 田間適應實測報表已存檔至: {report_file}")

    # 繪製對比圖
    fig, ax = plt.subplots(figsize=(10, 6))
    names = [r["name"] for r in results]
    pre_scores = [r["pre_field_acc"] for r in results]
    post_scores = [r["post_field_acc"] for r in results]
    gains = [r["gain"] for r in results]

    x = np.arange(len(names))
    width = 0.35

    bars1 = ax.bar(x - width/2, pre_scores, width, label="微調前 (純 PlantVillage 權重)", color="#B0BEC5", edgecolor="black", linewidth=1.1)
    bars2 = ax.bar(x + width/2, post_scores, width, label="微調後 (PlantVillage + 田間影像混合訓練)", color=[r["color"] for r in results], edgecolor="black", linewidth=1.1)

    ax.set_ylabel("獨立田間盲測集 Top-1 準確率 (%)", fontsize=12, fontweight="bold")
    ax.set_title("【大家一起套上田間資料訓練：四架構實戰對決與模型容量天花板】\n(2,260 張田間微調 vs 2,260 張未見過獨立田間盲測)", fontsize=13, fontweight="bold", pad=15)
    ax.set_xticks(x)
    ax.set_xticklabels(names, fontsize=10.5, fontweight="bold")
    ax.set_ylim(60, 100)
    ax.grid(axis="y", linestyle="--", alpha=0.5)
    ax.legend(loc="upper right", frameon=True, fontsize=10.5)

    for bar, val in zip(bars1, pre_scores):
        ax.text(bar.get_x() + bar.get_width()/2, val + 0.6, f"{val:.1f}%", ha="center", va="bottom", fontsize=9.5, color="#546E7A", fontweight="bold")

    for bar, val, g in zip(bars2, post_scores, gains):
        ax.text(bar.get_x() + bar.get_width()/2, val + 0.6, f"{val:.1f}%\n(+{g:.1f}%)", ha="center", va="bottom", fontsize=9.5, fontweight="bold")

    plt.tight_layout()
    chart_file = ARTIFACTS_DIR / "chart_field_adaptation_comparison.png"
    plt.savefig(chart_file, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"📊 田間適應對比圖已生成: {chart_file}")


if __name__ == "__main__":
    run_experiment()
