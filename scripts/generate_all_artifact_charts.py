import os
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")
import matplotlib
import matplotlib.pyplot as plt
import numpy as np

# 設定微軟正黑體以支援繁體中文
plt.rcParams['font.sans-serif'] = ['Microsoft JhengHei', 'DejaVu Sans', 'Arial']
plt.rcParams['axes.unicode_minus'] = False
matplotlib.rcParams['figure.dpi'] = 300

ARTIFACTS_DIR = Path(r"d:\plant_backend\artifacts")
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

# 現代質感專業配色盤
PRIMARY_COLOR = "#2E7D32"     # 墨綠 (代表冠軍級聯/Gemini)
SECONDARY_COLOR = "#1565C0"   # 深藍 (代表本地端ConvNeXt)
ACCENT_RED = "#C62828"        # 磚紅 (代表改錯/倒扣)
ACCENT_ORANGE = "#EF6C00"     # 暖橘 (代表GPT-4o)
ACCENT_PURPLE = "#6A1B9A"     # 紫色 (代表Claude)
BG_GRID = "#E0E0E0"


def generate_chart1_multi_ai_400():
    """圖表 1: 400 張多模型級聯大對決總成績 (Multi-AI Cascade 400 Benchmark)"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

    # 子圖 1: 總體 400 張準確率
    models = ['級聯 + Gemini 3.8\n(冠軍)', '本地 ConvNeXt\n(純端側)', '級聯 + GPT-4o\n(OpenAI)', '級聯 + Claude Sonnet 5\n(Anthropic)']
    accs = [75.75, 66.75, 57.50, 56.25]
    colors = [PRIMARY_COLOR, SECONDARY_COLOR, ACCENT_ORANGE, ACCENT_PURPLE]
    bars1 = ax1.bar(models, accs, color=colors, width=0.55, edgecolor='black', linewidth=1.2)

    ax1.set_ylim(0, 90)
    ax1.set_ylabel('總體診斷準確率 (%)', fontsize=12, fontweight='bold')
    ax1.set_title('【全量 400 張病害診斷總體準確率】\n(涵蓋 55 類病害，端側快篩 56% 請求)', fontsize=13, fontweight='bold', pad=15)
    ax1.grid(axis='y', linestyle='--', alpha=0.6, color=BG_GRID)

    for bar in bars1:
        yval = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2.0, yval + 1.5, f'{yval:.2f}%', ha='center', va='bottom', fontsize=11, fontweight='bold')

    ax1.axhline(66.75, color=SECONDARY_COLOR, linestyle=':', alpha=0.8, linewidth=1.5, label='本地 ConvNeXt 基準線 (66.75%)')
    ax1.legend(loc='upper right', frameon=True)

    # 子圖 2: 176 張極限疑難病害 (純雲端盲測)
    cloud_models = ['Gemini 3.8 Flash', 'OpenAI GPT-4o', 'Claude Sonnet 5']
    cloud_accs = [67.05, 25.57, 22.73]
    cloud_colors = [PRIMARY_COLOR, ACCENT_ORANGE, ACCENT_PURPLE]
    bars2 = ax2.bar(cloud_models, cloud_accs, color=cloud_colors, width=0.48, edgecolor='black', linewidth=1.2)

    ax2.set_ylim(0, 80)
    ax2.set_ylabel('困難樣本純盲測準確率 (%)', fontsize=12, fontweight='bold')
    ax2.set_title('【176 張極限疑難病害純雲端盲測對決】\n(本地信心度 < 0.70 之邊界樣本)', fontsize=13, fontweight='bold', pad=15)
    ax2.grid(axis='y', linestyle='--', alpha=0.6, color=BG_GRID)

    for bar in bars2:
        yval = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2.0, yval + 1.5, f'{yval:.2f}%\n({int(yval*1.76)}/176)', ha='center', va='bottom', fontsize=11, fontweight='bold')

    plt.tight_layout()
    out_path = ARTIFACTS_DIR / "chart1_multi_ai_400_comparison.png"
    plt.savefig(out_path, dpi=300)
    plt.close()
    print(f"✅ 生成圖表 1: {out_path.name}")


def generate_chart2_negative_transfer():
    """圖表 2: 有害兜底現象拆解 (Negative Transfer & Harmful Fallback)"""
    fig, ax = plt.subplots(figsize=(11, 6))

    models = ['Google Gemini 3.8 Flash', 'OpenAI GPT-4o', 'Anthropic Claude Sonnet 5']
    fixed = [57, 18, 13]         # 救回題數 (ConvNeXt錯，AI對)
    overwrote = [21, 55, 55]     # 改錯題數 (ConvNeXt原本對，AI硬改成錯)
    net = [36, -37, -42]         # 淨增減題數

    x = np.arange(len(models))
    width = 0.28

    rects1 = ax.bar(x - width, fixed, width, label='正向救回題數 (ConvNeXt答錯 -> 雲端AI救回)', color='#388E3C', edgecolor='black', linewidth=1.1)
    rects2 = ax.bar(x, overwrote, width, label='逆向改錯題數 (ConvNeXt答對 -> 雲端AI改錯)', color='#D32F2F', edgecolor='black', linewidth=1.1)
    
    # 淨貢獻長條
    net_colors = ['#1B5E20' if val > 0 else '#B71C1C' for val in net]
    rects3 = ax.bar(x + width, net, width, label='淨貢獻題數 (救回減改錯)', color=net_colors, edgecolor='black', linewidth=1.1, hatch='//')

    ax.set_ylabel('樣本題數 (張)', fontsize=12, fontweight='bold')
    ax.set_title('【級聯策略「有害兜底 (Harmful Fallback)」機制深入剖析】\n為什麼換上 GPT-4o / Claude 總成績反而被大幅倒扣？', fontsize=14, fontweight='bold', pad=15)
    ax.set_xticks(x)
    ax.set_xticklabels(models, fontsize=11, fontweight='bold')
    ax.legend(loc='upper right', frameon=True, fontsize=10)
    ax.grid(axis='y', linestyle='--', alpha=0.6, color=BG_GRID)
    ax.axhline(0, color='black', linewidth=1)

    # 標記數字
    for rect in rects1:
        h = rect.get_height()
        ax.text(rect.get_x() + rect.get_width()/2., h + 1, f'+{h}', ha='center', va='bottom', fontsize=10, fontweight='bold')
    for rect in rects2:
        h = rect.get_height()
        ax.text(rect.get_x() + rect.get_width()/2., h + 1, f'{h}', ha='center', va='bottom', fontsize=10, fontweight='bold')
    for rect in rects3:
        h = rect.get_height()
        sign = '+' if h > 0 else ''
        pos = h + 1 if h > 0 else h - 4
        ax.text(rect.get_x() + rect.get_width()/2., pos, f'{sign}{h}', ha='center', va='bottom', fontsize=11, fontweight='bold', color=rect.get_facecolor())

    ax.set_ylim(-55, 75)
    plt.tight_layout()
    out_path = ARTIFACTS_DIR / "chart2_negative_transfer_breakdown.png"
    plt.savefig(out_path, dpi=300)
    plt.close()
    print(f"✅ 生成圖表 2: {out_path.name}")


def generate_chart3_plantdoc_ablation():
    """圖表 3: PlantDoc 自然田間 236 張三策略消融評測"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5.5))

    strategies = ['純本地 ConvNeXt\n(Small 微調版)', '純雲端 Gemini 3.8\n(Flash 官方版)', '級聯混合策略\n(本專題核心)']
    accs = [66.53, 74.58, 78.39]
    latencies = [66, 1180, 560]
    colors = [SECONDARY_COLOR, ACCENT_ORANGE, PRIMARY_COLOR]

    # 準確率
    bars1 = ax1.bar(strategies, accs, color=colors, width=0.52, edgecolor='black', linewidth=1.2)
    ax1.set_ylim(0, 92)
    ax1.set_ylabel('診斷準確率 (%)', fontsize=12, fontweight='bold')
    ax1.set_title('【PlantDoc 自然田間 236 張全量消融準確率】\n(In-the-Wild 複雜背景與反光環境)', fontsize=13, fontweight='bold', pad=15)
    ax1.grid(axis='y', linestyle='--', alpha=0.6, color=BG_GRID)

    for bar in bars1:
        yval = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2.0, yval + 1.5, f'{yval:.2f}%', ha='center', va='bottom', fontsize=11, fontweight='bold')

    # 延遲與成本
    bars2 = ax2.bar(strategies, latencies, color=colors, width=0.52, edgecolor='black', linewidth=1.2)
    ax2.set_ylim(0, 1400)
    ax2.set_ylabel('平均診斷延遲 (毫秒 ms)', fontsize=12, fontweight='bold')
    ax2.set_title('【端雲延遲與 API 調用優化對比】\n(級聯策略節省 55.5% 雲端 API 消耗)', fontsize=13, fontweight='bold', pad=15)
    ax2.grid(axis='y', linestyle='--', alpha=0.6, color=BG_GRID)

    for bar in bars2:
        yval = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2.0, yval + 30, f'{int(yval)} ms', ha='center', va='bottom', fontsize=11, fontweight='bold')

    plt.tight_layout()
    out_path = ARTIFACTS_DIR / "chart3_plantdoc_three_strategies.png"
    plt.savefig(out_path, dpi=300)
    plt.close()
    print(f"✅ 生成圖表 3: {out_path.name}")


def generate_chart4_ai_challenger():
    """圖表 4: AI Challenger 55 類代表性測試與 248 張馬拉松大盲測對比"""
    fig, ax = plt.subplots(figsize=(10, 5.5))

    datasets = ['AI Challenger 55 類代表性盲測 (55張)', 'AI Challenger 全域馬拉松大盲測 (248張)']
    x = np.arange(len(datasets))
    width = 0.25

    conv_acc = [56.4, 93.95]
    gem_acc = [60.0, 90.73]
    cas_acc = [70.9, 95.56]

    rects1 = ax.bar(x - width, conv_acc, width, label='純本地 ConvNeXt', color=SECONDARY_COLOR, edgecolor='black', linewidth=1.1)
    rects2 = ax.bar(x, gem_acc, width, label='純雲端 Gemini 3.8', color=ACCENT_ORANGE, edgecolor='black', linewidth=1.1)
    rects3 = ax.bar(x + width, cas_acc, width, label='級聯混合策略 (雙強協同)', color=PRIMARY_COLOR, edgecolor='black', linewidth=1.1)

    ax.set_ylabel('準確率 (%)', fontsize=12, fontweight='bold')
    ax.set_title('【AI Challenger 跨規模對照盲測】\n級聯策略在不同資料規模下均全面超越單一模型', fontsize=13, fontweight='bold', pad=15)
    ax.set_xticks(x)
    ax.set_xticklabels(datasets, fontsize=11, fontweight='bold')
    ax.set_ylim(0, 110)
    ax.legend(loc='upper left', frameon=True)
    ax.grid(axis='y', linestyle='--', alpha=0.6, color=BG_GRID)

    def autolabel(rects):
        for rect in rects:
            h = rect.get_height()
            ax.text(rect.get_x() + rect.get_width()/2., h + 1.5, f'{h:.1f}%', ha='center', va='bottom', fontsize=10, fontweight='bold')

    autolabel(rects1)
    autolabel(rects2)
    autolabel(rects3)

    plt.tight_layout()
    out_path = ARTIFACTS_DIR / "chart4_ai_challenger_comparisons.png"
    plt.savefig(out_path, dpi=300)
    plt.close()
    print(f"✅ 生成圖表 4: {out_path.name}")


def generate_chart5_finetune_impact():
    """圖表 5: 本地 ConvNeXt 遷移學習微調前後跨域準確率躍升"""
    fig, ax = plt.subplots(figsize=(8, 5.5))

    stages = ['原始未微調權重\n(受限於實驗室背景)', 'PlantDoc 田間微調後最佳權重\n(適應光影/雜草/自然反光)']
    accs = [24.58, 66.53]
    colors = ['#757575', SECONDARY_COLOR]

    bars = ax.bar(stages, accs, color=colors, width=0.45, edgecolor='black', linewidth=1.2)
    ax.set_ylim(0, 85)
    ax.set_ylabel('PlantDoc 測試集準確率 (%)', fontsize=12, fontweight='bold')
    ax.set_title('【本地 ConvNeXt 邊緣端遷移學習微調增益】\n克服「實驗室單一背景」到「真實農田」之領域偏移 (Domain Shift)', fontsize=13, fontweight='bold', pad=15)
    ax.grid(axis='y', linestyle='--', alpha=0.6, color=BG_GRID)

    for bar in bars:
        yval = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2.0, yval + 1.5, f'{yval:.2f}%', ha='center', va='bottom', fontsize=12, fontweight='bold')

    # 繪製飛躍上升箭頭
    ax.annotate(
        '準確率狂飆 +41.95%！\n(端側快篩命中率翻倍)',
        xy=(1, 66.53), xytext=(0.5, 48),
        arrowprops=dict(facecolor=ACCENT_RED, shrink=0.08, width=2.5, headwidth=9),
        fontsize=11, fontweight='bold', color=ACCENT_RED,
        bbox=dict(boxstyle="round,pad=0.4", fc="#FFEBEE", ec=ACCENT_RED, lw=1.2)
    )

    plt.tight_layout()
    out_path = ARTIFACTS_DIR / "chart5_convnext_finetuning_impact.png"
    plt.savefig(out_path, dpi=300)
    plt.close()
    print(f"✅ 生成圖表 5: {out_path.name}")


def generate_chart6_dashboard():
    """圖表 6: 全系統核心數據綜合儀表板 (海報 / PPT 專用)"""
    fig, axes = plt.subplots(2, 2, figsize=(15, 11))
    fig.suptitle('智慧植物病害雲端協同診斷系統 (Plant AI) —— 核心評測數據全覽儀表板', fontsize=16, fontweight='bold', y=0.98)

    # 1. 四大多模型 400 張總評測
    ax1 = axes[0, 0]
    m_names = ['級聯+Gemini', '純ConvNeXt', '級聯+GPT4o', '級聯+Claude']
    m_acc = [75.75, 66.75, 57.50, 56.25]
    bars = ax1.bar(m_names, m_acc, color=[PRIMARY_COLOR, SECONDARY_COLOR, ACCENT_ORANGE, ACCENT_PURPLE], width=0.5, edgecolor='black')
    ax1.set_ylim(0, 90)
    ax1.set_title('A. 400張多模型級聯大對決總準確率', fontsize=12, fontweight='bold')
    ax1.set_ylabel('準確率 (%)', fontsize=10, fontweight='bold')
    ax1.grid(axis='y', linestyle='--', alpha=0.5)
    for b in bars:
        ax1.text(b.get_x() + b.get_width()/2., b.get_height() + 1.2, f'{b.get_height():.1f}%', ha='center', va='bottom', fontsize=10, fontweight='bold')

    # 2. 176張極難病害盲測
    ax2 = axes[0, 1]
    c_names = ['Gemini 3.8', 'GPT-4o', 'Claude 5']
    c_acc = [67.05, 25.57, 22.73]
    bars2 = ax2.bar(c_names, c_acc, color=[PRIMARY_COLOR, ACCENT_ORANGE, ACCENT_PURPLE], width=0.45, edgecolor='black')
    ax2.set_ylim(0, 80)
    ax2.set_title('B. 176張極限疑難病害純盲測對決 (作物與病斑雙重檢驗)', fontsize=12, fontweight='bold')
    ax2.set_ylabel('準確率 (%)', fontsize=10, fontweight='bold')
    ax2.grid(axis='y', linestyle='--', alpha=0.5)
    for b in bars2:
        ax2.text(b.get_x() + b.get_width()/2., b.get_height() + 1.2, f'{b.get_height():.1f}%', ha='center', va='bottom', fontsize=10, fontweight='bold')

    # 3. 救題 vs 改錯題 (有害兜底拆解)
    ax3 = axes[1, 0]
    nets = [36, -37, -42]
    net_cols = [PRIMARY_COLOR, ACCENT_RED, ACCENT_RED]
    bars3 = ax3.bar(c_names, nets, color=net_cols, width=0.45, edgecolor='black', hatch='//')
    ax3.set_ylim(-50, 48)
    ax3.axhline(0, color='black', linewidth=1)
    ax3.set_title('C. 雲端AI接手後淨貢獻題數 (正向救回題 - 逆向改錯題)', fontsize=12, fontweight='bold')
    ax3.set_ylabel('淨貢獻題數 (張)', fontsize=10, fontweight='bold')
    ax3.grid(axis='y', linestyle='--', alpha=0.5)
    for b in bars3:
        h = b.get_height()
        pos = h + 1.5 if h > 0 else h - 4.5
        ax3.text(b.get_x() + b.get_width()/2., pos, f'{"+" if h > 0 else ""}{h}', ha='center', va='bottom', fontsize=11, fontweight='bold', color=b.get_facecolor())

    # 4. PlantDoc 三策略消融 (準確率 vs 延遲)
    ax4 = axes[1, 1]
    s_names = ['純端側 ConvNeXt', '純雲端 Gemini', '級聯混合策略']
    s_acc = [66.53, 74.58, 78.39]
    s_lat = [66, 1180, 560]
    
    color_bar = [SECONDARY_COLOR, ACCENT_ORANGE, PRIMARY_COLOR]
    ax4_sub = ax4.twinx()
    
    b_acc = ax4.bar(np.arange(3) - 0.18, s_acc, width=0.35, color=color_bar, edgecolor='black', label='準確率 (%)')
    b_lat = ax4_sub.bar(np.arange(3) + 0.18, s_lat, width=0.35, color='#B0BEC5', edgecolor='black', hatch='..', label='延遲 (ms)')
    
    ax4.set_xticks(range(3))
    ax4.set_xticklabels(s_names, fontsize=10, fontweight='bold')
    ax4.set_ylim(0, 95)
    ax4_sub.set_ylim(0, 1400)
    ax4.set_ylabel('診斷準確率 (%)', fontsize=10, fontweight='bold')
    ax4_sub.set_ylabel('平均延遲 (ms)', fontsize=10, fontweight='bold')
    ax4.set_title('D. 軟硬體協同性能消融 (PlantDoc 自然田間評測)', fontsize=12, fontweight='bold')
    
    for b in b_acc:
        ax4.text(b.get_x() + b.get_width()/2., b.get_height() + 1.5, f'{b.get_height():.1f}%', ha='center', va='bottom', fontsize=9, fontweight='bold')
    for b in b_lat:
        ax4_sub.text(b.get_x() + b.get_width()/2., b.get_height() + 25, f'{int(b.get_height())}ms', ha='center', va='bottom', fontsize=9, fontweight='bold')

    plt.tight_layout()
    out_path = ARTIFACTS_DIR / "chart6_comprehensive_architecture_dashboard.png"
    plt.savefig(out_path, dpi=300)
    plt.close()
    print(f"✅ 生成圖表 6: {out_path.name}")


if __name__ == "__main__":
    print("🎨 開始繪製各項實驗高解析專業圖表...")
    generate_chart1_multi_ai_400()
    generate_chart2_negative_transfer()
    generate_chart3_plantdoc_ablation()
    generate_chart4_ai_challenger()
    generate_chart5_finetune_impact()
    generate_chart6_dashboard()
    print("\n🎉 全部 6 張出版級高解析圖表已全數輸出至 artifacts/ 目錄！")
