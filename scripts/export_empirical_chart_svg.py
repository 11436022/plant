"""
將 chart_empirical_training_comparison 匯出為高畫質向量 SVG 檔。
讀取 artifacts/empirical_training_benchmark_report.json 數據進行繪製。
"""

import json
import sys
from pathlib import Path
import matplotlib
import matplotlib.pyplot as plt
import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# 設置 SVG 與字型
matplotlib.rcParams['svg.fonttype'] = 'none'  # 保留文字為 <text> 標籤，便於縮放與編輯
plt.rcParams['font.sans-serif'] = ['Microsoft JhengHei', 'DejaVu Sans', 'Arial']
plt.rcParams['axes.unicode_minus'] = False
matplotlib.rcParams['figure.dpi'] = 300

ROOT_DIR = Path(__file__).resolve().parents[1]
ARTIFACTS_DIR = ROOT_DIR / "artifacts"
REPORT_PATH = ARTIFACTS_DIR / "empirical_training_benchmark_report.json"

if not REPORT_PATH.exists():
    raise FileNotFoundError(f"找不到報告檔案: {REPORT_PATH}")

with open(REPORT_PATH, "r", encoding="utf-8") as f:
    data = json.load(f)

results = data["models"]

fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))

names = [r["name"] for r in results]
colors = [r["color"] for r in results]
top1s = [r["final_val_top1"] for r in results]
top3s = [r["final_val_top3"] for r in results]
params = [r["params_m"] for r in results]
train_times = [r["total_train_time_sec"] for r in results]
latencies = [r["val_latency_ms"] for r in results]

# 子圖 1: 全量 17,572 張驗證集真實 Top-1 準確率
bars1 = ax1.bar(names, top1s, color=colors, edgecolor="black", width=0.55, linewidth=1.2)
ax1.set_ylabel("真實驗證集 Top-1 準確率 (%)", fontsize=12, fontweight="bold")
ax1.set_title("【本機同條件微調：全量 17,572 張驗證集 Top-1 準確率】\n(相同 Epoch、相同 Learning Rate、相同資料隨機種子)", fontsize=13, fontweight="bold", pad=12)
ax1.set_ylim(min(top1s) - 5, 100)
ax1.grid(axis="y", linestyle="--", alpha=0.5)

for bar, val in zip(bars1, top1s):
    ax1.text(bar.get_x() + bar.get_width() / 2.0, val + 0.6, f"{val:.2f}%", ha="center", va="bottom", fontsize=11, fontweight="bold")

# 子圖 2: 訓練 Loss 歷程收斂曲線
epochs_range = range(1, len(results[0]["history"]["train_loss"]) + 1)
for r in results:
    ax2.plot(epochs_range, r["history"]["train_loss"], marker="o", linewidth=2.2, color=r["color"], label=f"{r['name']} (最終: {r['final_train_loss']:.3f})")
ax2.set_xlabel("訓練輪數 (Epoch)", fontsize=12, fontweight="bold")
ax2.set_ylabel("交叉熵損失 (CrossEntropy Loss)", fontsize=12, fontweight="bold")
ax2.set_title("【模型訓練收斂損失曲線 (Train Loss)】\n(驗證 ConvNeXt 在細粒度特徵學習上的收斂優勢)", fontsize=13, fontweight="bold", pad=12)
ax2.set_xticks(list(epochs_range))
ax2.grid(True, linestyle="--", alpha=0.5)
ax2.legend(loc="upper right", frameon=True, fontsize=10)

# 子圖 3: 參數量 vs 最終驗證精度 (真實邊界分析)
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

# 子圖 4: 總訓練耗時與單張推論延遲
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

print(f"✅ PNG 圖表已更新: {png_path}")
print(f"✅ SVG 向量圖表已更新: {svg_path}")
