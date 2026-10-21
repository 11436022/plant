"""
生成更新後的 chart_lab_vs_field_reality (PNG 與向量 SVG)
將 ResNet-50 統一換成典雅深紫色 (#6A1B9A)，確保與 MobileNet 藍色明確區隔。
"""

import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

import matplotlib
import matplotlib.pyplot as plt
import numpy as np

# 設置繪圖環境
matplotlib.rcParams['svg.fonttype'] = 'none'
plt.rcParams['font.sans-serif'] = ['Microsoft JhengHei', 'DejaVu Sans', 'Arial']
plt.rcParams['axes.unicode_minus'] = False
matplotlib.rcParams['figure.dpi'] = 300

ROOT_DIR = Path(__file__).resolve().parents[1]
ARTIFACTS_DIR = ROOT_DIR / "artifacts"
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

# 統一配色盤 (ResNet-50 改為深紫色 #6A1B9A)
COLOR_CONVNEXT = "#1B5E20"     # 深綠
COLOR_EFFICIENT = "#E65100"    # 亮橘
COLOR_MOBILENET = "#0277BD"    # 湛藍
COLOR_RESNET = "#6A1B9A"       # 典雅深紫 (已更換，與藍色明確區隔)

def generate_chart():
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))

    models = ["ConvNeXt-Small\n(本專案核心)", "EfficientNet-B0\n(Google 複合縮放)", "MobileNetV3-L\n(邊緣行動端)", "ResNet-50\n(學術金標竿)"]
    colors = [COLOR_CONVNEXT, COLOR_EFFICIENT, COLOR_MOBILENET, COLOR_RESNET]

    # 左圖: 實驗室環境 (PlantVillage)
    lab_accs = [98.45, 95.76, 95.21, 84.85]
    bars1 = ax1.bar(models, lab_accs, color=colors, width=0.55, edgecolor="black", linewidth=1.2)
    ax1.set_ylim(70, 105)
    ax1.set_ylabel("Top-1 準確率 (%)", fontsize=12, fontweight="bold")
    ax1.set_title("【實驗室受控環境：PlantVillage 17,572 張】\n(背景單純乾淨，模型多數飽和在 95%~98%)", fontsize=13, fontweight="bold", pad=14)
    ax1.grid(axis="y", linestyle="--", alpha=0.5)

    for bar, val in zip(bars1, lab_accs):
        ax1.text(bar.get_x() + bar.get_width() / 2.0, val + 0.8, f"{val:.2f}%", ha="center", va="bottom", fontsize=11, fontweight="bold")

    # 右圖: 真實環境 (AI Challenger / In-the-Wild)
    field_accs = [85.46, 81.92, 80.77, 72.61]
    bars2 = ax2.bar(models, field_accs, color=colors, width=0.55, edgecolor="black", linewidth=1.2)
    ax2.set_ylim(60, 95)
    ax2.set_ylabel("Top-1 準確率 (%)", fontsize=12, fontweight="bold")
    ax2.set_title("【真實日常與非受控實景：AI Challenger 4,520 張】\n(強光、泥土、反光、重疊葉片，差距瞬間拉開 13%!)", fontsize=13, fontweight="bold", pad=14)
    ax2.grid(axis="y", linestyle="--", alpha=0.5)

    for bar, val in zip(bars2, field_accs):
        ax2.text(bar.get_x() + bar.get_width() / 2.0, val + 0.7, f"{val:.2f}%", ha="center", va="bottom", fontsize=11, fontweight="bold")

    # 標記實戰差距拉開綠色箭頭
    ax2.annotate(
        "實戰差距拉開:\n+12.85%!",
        xy=(0, 85.46),
        xytext=(0.35, 90.0),
        fontsize=10.5,
        fontweight="bold",
        color="#1B5E20",
        arrowprops=dict(facecolor="#1B5E20", shrink=0.08, width=2.0, headwidth=8),
        ha="center"
    )

    plt.tight_layout()

    png_path = ARTIFACTS_DIR / "chart_lab_vs_field_reality.png"
    plt.savefig(png_path, dpi=300, bbox_inches="tight")

    svg_path = ARTIFACTS_DIR / "chart_lab_vs_field_reality.svg"
    plt.savefig(svg_path, format="svg", bbox_inches="tight")
    plt.close()

    print(f"✅ 已成功生成: {png_path}")
    print(f"✅ 已成功生成: {svg_path}")

if __name__ == "__main__":
    generate_chart()

