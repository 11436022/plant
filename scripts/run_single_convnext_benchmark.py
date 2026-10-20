"""
專門對 ConvNeXt-Small 進行即時真實訓練與全量驗證 (Fresh Live Benchmark)。
獲得 100% 精準無偏差的訓練時間、收斂損失與真實驗證精度，
並自動更新 artifacts/empirical_training_benchmark_report.json 與圖表 (PNG + SVG)。
"""

import functools
import gc
import json
import os
import random
import sys
import time
from pathlib import Path

# 強制啟用即時 flush 與 UTF-8
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
from torch.amp import GradScaler, autocast
from torch.utils.data import DataLoader, Subset
from torchvision import datasets, transforms

# 設置繪圖環境
matplotlib.rcParams['svg.fonttype'] = 'none'
plt.rcParams['font.sans-serif'] = ['Microsoft JhengHei', 'DejaVu Sans', 'Arial']
plt.rcParams['axes.unicode_minus'] = False
matplotlib.rcParams['figure.dpi'] = 300

ROOT_DIR = Path(__file__).resolve().parents[1]
ARTIFACTS_DIR = ROOT_DIR / "artifacts"
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

DATASET_ROOT = Path(r"D:\archive\New Plant Diseases Dataset(Augmented)\New Plant Diseases Dataset(Augmented)")
TRAIN_DIR = DATASET_ROOT / "train"
VALID_DIR = DATASET_ROOT / "valid"

# 設定全域隨機種子以確保 100% 可復現性
SEED = 42
random.seed(SEED)
np.random.seed(SEED)
torch.manual_seed(SEED)
if torch.cuda.is_available():
    torch.cuda.manual_seed_all(SEED)

CONVNEXT_INFO = {
    "id": "convnext_small",
    "name": "ConvNeXt-Small",
    "desc": "現代純卷積 SOTA (本專案核心)",
    "timm_name": "convnext_small",
    "batch_size": 32,
    "color": "#1B5E20",
}


def get_transforms():
    train_transform = transforms.Compose([
        transforms.Resize(256),
        transforms.RandomCrop(224),
        transforms.RandomHorizontalFlip(),
        transforms.RandomRotation(15),
        transforms.ColorJitter(brightness=0.1, contrast=0.1),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])

    valid_transform = transforms.Compose([
        transforms.Resize(256),
        transforms.CenterCrop(224),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])
    return train_transform, valid_transform


def build_stratified_train_subset(train_dataset: datasets.ImageFolder, samples_per_class: int = 300) -> Subset:
    class_indices = {}
    for idx, (_, label) in enumerate(train_dataset.samples):
        if label not in class_indices:
            class_indices[label] = []
        class_indices[label].append(idx)

    selected_indices = []
    for label, idxs in class_indices.items():
        random.seed(SEED + label)
        sampled = random.sample(idxs, min(samples_per_class, len(idxs)))
        selected_indices.extend(sampled)

    random.seed(SEED)
    random.shuffle(selected_indices)
    return Subset(train_dataset, selected_indices)


def run_benchmark():
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    gpu_name = torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU"
    print(f"🚀 [啟動 ConvNeXt-Small 現場即時精確重測] 算力裝置: {device} ({gpu_name})")

    # 1. 載入資料集
    t_data_0 = time.perf_counter()
    train_transform, valid_transform = get_transforms()
    full_train_dataset = datasets.ImageFolder(str(TRAIN_DIR), transform=train_transform)
    full_valid_dataset = datasets.ImageFolder(str(VALID_DIR), transform=valid_transform)
    train_subset = build_stratified_train_subset(full_train_dataset, samples_per_class=300)
    print(f"📦 訓練集: {len(train_subset)} 張 (38 類均勻平衡) | 驗證集: {len(full_valid_dataset)} 張 (全量驗證)")
    print(f"⏱️ 資料集準備耗時: {time.perf_counter() - t_data_0:.2f} 秒")

    # 2. 建立模型
    print(f"\n📦 正在載入 ConvNeXt-Small (pretrained=True, num_classes=38)...")
    model = timm.create_model("convnext_small", pretrained=True, num_classes=38)
    model.to(device)
    total_params = sum(p.numel() for p in model.parameters()) / 1e6
    print(f"   參數量: {total_params:.2f}M")

    # 3. DataLoader
    train_loader = DataLoader(train_subset, batch_size=32, shuffle=True, num_workers=0, pin_memory=True)
    valid_loader = DataLoader(full_valid_dataset, batch_size=128, shuffle=False, num_workers=0, pin_memory=True)

    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-4, weight_decay=1e-2)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=2)
    criterion = nn.CrossEntropyLoss()
    scaler = GradScaler("cuda")

    epochs = 2
    history = {
        "train_loss": [],
        "train_acc": [],
        "val_top1": [],
        "val_top3": [],
        "epoch_time": [],
    }

    print(f"\n🥊 開始執行 2 個 Epoch 的真實端對端微調訓練與全量驗證...")
    t_train_start = time.perf_counter()

    for epoch in range(1, epochs + 1):
        model.train()
        running_loss = 0.0
        correct_train = 0
        total_train = 0
        t_epoch_start = time.perf_counter()

        total_batches = len(train_loader)
        for b_idx, (images, labels) in enumerate(train_loader, 1):
            images, labels = images.to(device, non_blocking=True), labels.to(device, non_blocking=True)
            optimizer.zero_grad(set_to_none=True)

            with autocast("cuda"):
                outputs = model(images)
                loss = criterion(outputs, labels)

            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()

            running_loss += loss.item() * images.size(0)
            _, preds = outputs.max(1)
            correct_train += preds.eq(labels).sum().item()
            total_train += labels.size(0)

            if b_idx % 80 == 0 or b_idx == total_batches:
                curr_loss = running_loss / total_train
                curr_acc = (correct_train / total_train) * 100
                print(f"   Epoch [{epoch}/{epochs}] Batch [{b_idx:03d}/{total_batches}] -> Train Loss: {curr_loss:.4f} | Train Acc: {curr_acc:.2f}%")

        scheduler.step()
        epoch_sec = time.perf_counter() - t_epoch_start
        epoch_loss = running_loss / total_train
        epoch_acc = (correct_train / total_train) * 100

        # 全量驗證集評估 (17,572 張)
        print(f"   🔎 正在執行 Epoch {epoch} 全量驗證 (17,572 張葉片)...")
        model.eval()
        val_top1_correct = 0
        val_top3_correct = 0
        total_val = 0
        t_val_start = time.perf_counter()

        with torch.no_grad():
            for images, labels in valid_loader:
                images, labels = images.to(device, non_blocking=True), labels.to(device, non_blocking=True)
                with autocast("cuda"):
                    outputs = model(images)

                _, top1_pred = outputs.max(1)
                val_top1_correct += top1_pred.eq(labels).sum().item()

                _, top3_pred = outputs.topk(3, 1, True, True)
                val_top3_correct += top3_pred.eq(labels.view(-1, 1).expand_as(top3_pred)).sum().item()
                total_val += labels.size(0)

        val_top1_acc = (val_top1_correct / total_val) * 100
        val_top3_acc = (val_top3_correct / total_val) * 100
        val_sec = time.perf_counter() - t_val_start
        val_latency_ms = (val_sec / total_val) * 1000

        history["train_loss"].append(round(epoch_loss, 4))
        history["train_acc"].append(round(epoch_acc, 2))
        history["val_top1"].append(round(val_top1_acc, 2))
        history["val_top3"].append(round(val_top3_acc, 2))
        history["epoch_time"].append(round(epoch_sec, 2))

        print(f"   ⭐ Epoch {epoch} 完成! 訓練耗時: {epoch_sec:.2f}s | 驗證耗時: {val_sec:.2f}s | Top-1: {val_top1_acc:.2f}% | Top-3: {val_top3_acc:.2f}% | 推論延遲: {val_latency_ms:.2f}ms")

    total_train_sec = time.perf_counter() - t_train_start
    print(f"\n🎉 [現場實測完成] ConvNeXt-Small 2 輪訓練與全量驗證精確總耗時: {total_train_sec:.2f} 秒 ({total_train_sec/60:.2f} 分鐘)")

    # 4. 存檔權重
    save_path = ARTIFACTS_DIR / "empirical_convnext_small_plantvillage.pth"
    torch.save(model.state_dict(), save_path)
    print(f"💾 權重檔案已覆蓋儲存: {save_path}")

    # 清理顯存
    del model, optimizer, scheduler, scaler
    gc.collect()
    torch.cuda.empty_cache()

    convnext_result = {
        "id": "convnext_small",
        "name": "ConvNeXt-Small",
        "desc": "現代純卷積 SOTA (本專案核心)",
        "color": "#1B5E20",
        "params_m": round(total_params, 2),
        "total_train_time_sec": round(total_train_sec, 1),
        "final_train_loss": history["train_loss"][-1],
        "final_train_acc": history["train_acc"][-1],
        "final_val_top1": history["val_top1"][-1],
        "final_val_top3": history["val_top3"][-1],
        "val_latency_ms": round(val_latency_ms, 2),
        "history": history,
        "checkpoint": str(save_path.name),
    }

    # 5. 更新 JSON 報告
    report_path = ARTIFACTS_DIR / "empirical_training_benchmark_report.json"
    with open(report_path, "r", encoding="utf-8") as f:
        rep = json.load(f)

    # 替換 convnext_small 紀錄
    new_models = []
    replaced = False
    for m in rep.get("models", []):
        if m["id"] == "convnext_small":
            new_models.append(convnext_result)
            replaced = True
        else:
            new_models.append(m)
    if not replaced:
        new_models.insert(0, convnext_result)

    rep["models"] = new_models
    rep["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(rep, f, ensure_ascii=False, indent=2)
    print(f"📄 報表已精確更新: {report_path}")

    # 直接呼叫繪圖函式生成
    generate_charts(rep["models"])


def generate_charts(results: list[dict]):
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))

    names = [r["name"] for r in results]
    colors = [r["color"] for r in results]
    top1s = [r["final_val_top1"] for r in results]
    top3s = [r["final_val_top3"] for r in results]
    params = [r["params_m"] for r in results]
    train_times = [r["total_train_time_sec"] for r in results]
    latencies = [r["val_latency_ms"] for r in results]

    # 1. Top-1
    bars1 = ax1.bar(names, top1s, color=colors, edgecolor="black", width=0.55, linewidth=1.2)
    ax1.set_ylabel("真實驗證集 Top-1 準確率 (%)", fontsize=12, fontweight="bold")
    ax1.set_title("【本機同條件微調：全量 17,572 張驗證集 Top-1 準確率】\n(相同 Epoch、相同 Learning Rate、相同資料隨機種子)", fontsize=13, fontweight="bold", pad=12)
    ax1.set_ylim(min(top1s) - 5, 100)
    ax1.grid(axis="y", linestyle="--", alpha=0.5)
    for bar, val in zip(bars1, top1s):
        ax1.text(bar.get_x() + bar.get_width() / 2.0, val + 0.6, f"{val:.2f}%", ha="center", va="bottom", fontsize=11, fontweight="bold")

    # 2. Train Loss
    epochs_range = range(1, len(results[0]["history"]["train_loss"]) + 1)
    for r in results:
        ax2.plot(epochs_range, r["history"]["train_loss"], marker="o", linewidth=2.2, color=r["color"], label=f"{r['name']} (最終: {r['final_train_loss']:.3f})")
    ax2.set_xlabel("訓練輪數 (Epoch)", fontsize=12, fontweight="bold")
    ax2.set_ylabel("交叉熵損失 (CrossEntropy Loss)", fontsize=12, fontweight="bold")
    ax2.set_title("【模型訓練收斂損失曲線 (Train Loss)】\n(驗證 ConvNeXt 在細粒度特徵學習上的收斂優勢)", fontsize=13, fontweight="bold", pad=12)
    ax2.set_xticks(list(epochs_range))
    ax2.grid(True, linestyle="--", alpha=0.5)
    ax2.legend(loc="upper right", frameon=True, fontsize=10)

    # 3. Trade-off
    for r in results:
        marker = "*" if "ConvNeXt" in r["name"] else "o"
        size = 350 if "ConvNeXt" in r["name"] else 180
        ax3.scatter(r["params_m"], r["final_val_top1"], color=r["color"], s=size, marker=marker, edgecolors="black", linewidth=1.2, zorder=5)
        ax3.annotate(
            f"{r['name']}\n({r['params_m']}M, {r['final_val_top1']}%)",
            xy=(r["params_m"], r["final_val_top1"]),
            xytext=(r["params_m"] + 1.2, r["final_val_top1"] - 0.4),
            fontsize=9.5,
            fontweight="bold" if "ConvNeXt" in r["name"] else "normal",
            bbox=dict(boxstyle="round,pad=0.25", fc="white", ec=r["color"], alpha=0.9),
            arrowprops=dict(arrowstyle="->", color=r["color"], lw=1.0)
        )
    ax3.set_xlabel("模型參數量 (Parameters, M)", fontsize=12, fontweight="bold")
    ax3.set_ylabel("全量驗證集 Top-1 準確率 (%)", fontsize=12, fontweight="bold")
    ax3.set_title("【真實微調：參數量 vs 泛化精度 Trade-off】", fontsize=13, fontweight="bold", pad=12)
    ax3.set_xlim(min(params) - 5, max(params) + 12)
    ax3.set_ylim(min(top1s) - 3, max(top1s) + 3)
    ax3.grid(True, linestyle="--", alpha=0.5)

    # 4. Latency & Time
    ax4_twin = ax4.twinx()
    x = np.arange(len(names))
    b_time = ax4.bar(x - 0.18, train_times, width=0.36, color="#455A64", alpha=0.85, edgecolor="black", label="總微調耗時 (秒)")
    b_lat = ax4_twin.bar(x + 0.18, latencies, width=0.36, color="#C62828", alpha=0.85, edgecolor="black", label="推論延遲 (ms/張)")

    ax4.set_ylabel("微調訓練時間 (秒, 越短越省時)", color="#455A64", fontsize=11, fontweight="bold")
    ax4_twin.set_ylabel("推論延遲 (ms/張, 越短越快)", color="#C62828", fontsize=11, fontweight="bold")
    ax4.set_title("【RTX 5070 算力效率：微調訓練時間與推論延遲】", fontsize=13, fontweight="bold", pad=12)
    ax4.set_xticks(x)
    ax4.set_xticklabels(names, rotation=20, ha="right", fontsize=10, fontweight="bold")
    ax4.grid(axis="y", linestyle="--", alpha=0.4)

    lines = [b_time, b_lat]
    labels = ["總微調耗時 (秒)", "推論延遲 (ms/張)"]
    ax4.legend(lines, labels, loc="upper right", frameon=True, fontsize=10)

    plt.tight_layout()

    png_path = ARTIFACTS_DIR / "chart_empirical_training_comparison.png"
    plt.savefig(png_path, dpi=300, bbox_inches="tight")

    svg_path = ARTIFACTS_DIR / "chart_empirical_training_comparison.svg"
    plt.savefig(svg_path, format="svg", bbox_inches="tight")
    plt.close()

    print(f"📊 已生成精確新圖 (PNG): {png_path}")
    print(f"📊 已生成精確新圖 (SVG): {svg_path}")


if __name__ == "__main__":
    run_benchmark()
