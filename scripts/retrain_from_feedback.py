import os
import sys
import json
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
import argparse

# 確保專案根目錄在 sys.path 中
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from torchvision import transforms, datasets
import timm

from app.core.config import settings
from scripts.export_feedback_dataset import export_feedback_dataset

# 訓練影像標準增強預處理
train_transform = transforms.Compose([
    transforms.RandomResizedCrop(224, scale=(0.8, 1.0)),
    transforms.RandomHorizontalFlip(),
    transforms.RandomRotation(15),
    transforms.ColorJitter(brightness=0.15, contrast=0.15),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
])

val_transform = transforms.Compose([
    transforms.Resize(256),
    transforms.CenterCrop(224),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
])


def run_feedback_retraining(
    dataset_dir: Optional[Path] = None,
    epochs: int = 5,
    batch_size: int = 4,
    lr: float = 1e-4,
    auto_export: bool = True,
) -> Dict[str, Any]:
    """
    執行 ConvNeXt 回饋資料持續微調管線 (Continual Fine-Tuning Pipeline)。
    1. 匯出/確認田間標註資料集。
    2. 動態擴增分類頭輸出維度（相容全新長尾作物，如樺木、扁蒲）。
    3. 保留舊類別權重，微調分類頭與骨幹高階特徵。
    4. 自動安全備份並熱更新本地模型權重與類別索引。
    """
    if dataset_dir is None:
        dataset_dir = settings.BASE_DIR / "dataset" / "feedback_training"

    # 若資料集不存在或為空，自動先自 MySQL 導出
    if auto_export or not dataset_dir.exists() or len(list(dataset_dir.glob("*/*.*"))) == 0:
        print("[Retrain] 正在自回饋資料庫自動導出標註樣本...")
        export_feedback_dataset(output_dir=dataset_dir)

    # 檢查有效影像數量
    image_paths = list(dataset_dir.glob("*/*.*"))
    if not image_paths:
        return {
            "status": "skipped",
            "message": "資料集中無有效標註影像，請先於管理員後台標註使用者回饋！",
            "epochs_trained": 0,
        }

    print(f"[Retrain] 載入田間資料集，共 {len(image_paths)} 張標註影像...")
    dataset = datasets.ImageFolder(str(dataset_dir), transform=train_transform)
    dataloader = DataLoader(dataset, batch_size=min(batch_size, len(dataset)), shuffle=True)

    # 載入現有類別索引
    idx_path = Path(settings.CONVNEXT_CLASS_INDEX_PATH)
    if not idx_path.is_absolute():
        idx_path = settings.BASE_DIR / idx_path

    current_idx_to_class = {}
    if idx_path.exists():
        with open(idx_path, "r", encoding="utf-8") as f:
            raw = json.load(f)
            current_idx_to_class = {int(k): v for k, v in raw.items()}
    else:
        current_idx_to_class = {i: f"class_{i}" for i in range(38)}

    class_to_idx = {v: k for k, v in current_idx_to_class.items()}
    orig_num_classes = len(current_idx_to_class)

    # 檢查是否有新類別需要擴增分類頭
    new_classes = []
    for cls_name in dataset.classes:
        if cls_name not in class_to_idx:
            new_idx = len(current_idx_to_class)
            current_idx_to_class[new_idx] = cls_name
            class_to_idx[cls_name] = new_idx
            new_classes.append(cls_name)

    total_classes = len(current_idx_to_class)
    print(f"[Retrain] 原始類別數: {orig_num_classes}，新增類別數: {len(new_classes)}，擴增後總類別數: {total_classes}")

    # 載入現有模型權重
    model_path = Path(settings.CONVNEXT_MODEL_PATH)
    if not model_path.is_absolute():
        model_path = settings.BASE_DIR / model_path

    ckpt_classes = orig_num_classes
    if model_path.exists():
        state_dict = torch.load(str(model_path), map_location="cpu", weights_only=False)
        if "head.fc.weight" in state_dict:
            ckpt_classes = state_dict["head.fc.weight"].shape[0]
        model = timm.create_model("convnext_small", num_classes=ckpt_classes, pretrained=False)
        model.load_state_dict(state_dict, strict=False)
        print(f"[Retrain] 已載入既有模型權重 (Checkpoint 類別數: {ckpt_classes}): {model_path}")
    else:
        model = timm.create_model("convnext_small", num_classes=total_classes, pretrained=False)
        ckpt_classes = total_classes
        print(f"[WARN] 既有模型權重不存在，將以隨機權重初始化")

    # 若總類別數大於 Checkpoint 類別數，擴增分類頭 (Head FC Expansion) 並保留既有類別權重
    if total_classes > ckpt_classes:
        old_fc = model.head.fc
        in_feats = old_fc.in_features
        new_fc = nn.Linear(in_feats, total_classes)
        # 複製舊類別權重，確保原有類別辨識能力不退化
        with torch.no_grad():
            new_fc.weight[:ckpt_classes] = old_fc.weight
            if old_fc.bias is not None:
                new_fc.bias[:ckpt_classes] = old_fc.bias
        model.head.fc = new_fc
        print(f"[Retrain] 成功擴增分類頭權重矩陣 [{in_feats} -> {total_classes}]，舊類別知識完整保留！")

    # 設置微調優化器：分類頭較高學習率，骨幹微小學習率 (避免災難性遺忘)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    model.train()

    optimizer = torch.optim.AdamW([
        {"params": [p for n, p in model.named_parameters() if "head" not in n], "lr": lr * 0.1},
        {"params": model.head.parameters(), "lr": lr},
    ], weight_decay=1e-2)
    criterion = nn.CrossEntropyLoss()

    # 映射 dataset target 到全域 class_to_idx
    dataset_class_to_global_idx = [class_to_idx[dataset.classes[i]] for i in range(len(dataset.classes))]

    history = []
    print(f"[Retrain] 開始執行 {epochs} 輪微調 (裝置: {device})...")

    for epoch in range(1, epochs + 1):
        running_loss = 0.0
        correct = 0
        total = 0

        for images, targets in dataloader:
            images = images.to(device)
            # 轉換 target 為全域類別索引
            global_targets = torch.tensor([dataset_class_to_global_idx[t] for t in targets], device=device)

            optimizer.zero_grad()
            outputs = model(images)
            loss = criterion(outputs, global_targets)
            loss.backward()
            optimizer.step()

            running_loss += loss.item() * images.size(0)
            preds = torch.argmax(outputs, dim=1)
            correct += int((preds == global_targets).sum().item())
            total += images.size(0)

        epoch_loss = running_loss / max(1, total)
        epoch_acc = correct / max(1, total)
        history.append({
            "epoch": epoch,
            "loss": round(epoch_loss, 4),
            "accuracy": round(epoch_acc, 4),
        })
        print(f"  輪次 [{epoch}/{epochs}] - Loss: {epoch_loss:.4f}, Accuracy: {epoch_acc:.2%}")

    # 儲存與更新
    backup_path = model_path.with_suffix(".pth.bak")
    if model_path.exists():
        shutil.copy2(str(model_path), str(backup_path))
        print(f"[Retrain] 原模型已安全備份至: {backup_path}")

    # 儲存新權重
    torch.save(model.cpu().state_dict(), str(model_path))
    print(f"[OK] [Retrain] 新微調模型權重已儲存至: {model_path}")

    # 儲存更新後的類別映射
    with open(idx_path, "w", encoding="utf-8") as f:
        json.dump({str(k): v for k, v in current_idx_to_class.items()}, f, ensure_ascii=False, indent=2)
    print(f"[OK] [Retrain] 類別索引已同步更新: {idx_path}")

    # 儲存訓練日誌
    log_file = dataset_dir / "training_history.json"
    train_record = {
        "timestamp": datetime.now().isoformat(),
        "epochs": epochs,
        "sample_count": len(dataset),
        "total_classes": total_classes,
        "new_classes": new_classes,
        "history": history,
        "final_loss": history[-1]["loss"] if history else None,
        "final_accuracy": history[-1]["accuracy"] if history else None,
    }
    with open(log_file, "w", encoding="utf-8") as f:
        json.dump(train_record, f, ensure_ascii=False, indent=2)

    # 熱重載本地 ConvNeXt 模型與類別索引
    try:
        from app.services.convnext import get_convnext_model
        get_convnext_model(force_reload=True)
        print("[OK] [Retrain] 本地服務已熱加載最新微調權重與擴增類別！")
    except Exception as e:
        print(f"[WARN] 熱加載模型異常: {e}")

    # 重建視覺記憶索引，確保特徵空間同步
    try:
        from app.services.visual_memory import visual_memory
        visual_memory.rebuild_index()
    except Exception as e:
        print(f"[WARN] 觸發視覺記憶更新異常: {e}")

    return {
        "status": "success",
        "message": f"微調完成！共訓練 {epochs} 輪，覆蓋 {len(dataset)} 張標註影像，總類別數: {total_classes}。",
        "training_record": train_record,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ConvNeXt 回饋資料持續重訓微調腳本")
    parser.add_argument("--epochs", type=int, default=3, help="訓練輪數 (預設: 3)")
    parser.add_argument("--batch-size", type=int, default=4, help="Batch Size (預設: 4)")
    parser.add_argument("--lr", type=float, default=1e-4, help="學習率 (預設: 1e-4)")
    args = parser.parse_args()

    run_feedback_retraining(epochs=args.epochs, batch_size=args.batch_size, lr=args.lr)
