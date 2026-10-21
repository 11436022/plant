import sys
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

plt.rcParams['font.sans-serif'] = ['Microsoft JhengHei', 'DejaVu Sans', 'Arial']
plt.rcParams['axes.unicode_minus'] = False

ARTIFACTS_DIR = Path(r"d:\plant_backend\artifacts")
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

def draw_header(ax, title, subtitle):
    ax.text(50, 96.5, title, ha='center', va='center', fontsize=18, fontweight='bold', color='#1A237E')
    ax.text(50, 93.2, subtitle, ha='center', va='center', fontsize=11, color='#555555')

def generate_option1():
    """方案 1: 單頁直式分層 (由上到下，三大階段左側標籤)"""
    fig, ax = plt.subplots(figsize=(15, 9.5), dpi=300)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis('off')
    fig.patch.set_facecolor('#F8F9FA')

    draw_header(ax, "R02 : 如何防範 AI 幻覺與錯誤？—— 端雲協同多層防禦架構",
                "【方案 1：單頁垂直漏斗分層】由上至下清晰演繹：邊緣守門 -> 雲端會診 -> 處方拘束與閉環")

    # 階段 1
    p1 = patches.FancyBboxPatch((2, 65), 13, 24, boxstyle="round,pad=0.5", ec="#1B5E20", fc="#E8F5E9", lw=1.5)
    ax.add_patch(p1)
    ax.text(8.5, 77, "【第一階段】\n\n邊緣端前置\n品質與特徵守門\n\n[免調用 API\n4ms 快篩]", 
            ha='center', va='center', fontsize=10.5, fontweight='bold', color="#1B5E20")

    b1 = patches.FancyBboxPatch((17, 66.5), 36, 21, boxstyle="round,pad=0.5", ec="#2E7D32", fc="#FFFFFF", lw=1.5)
    ax.add_patch(b1)
    ax.text(18.5, 84.5, "1. 影像品質快篩 (Input Filter)", fontsize=11, fontweight='bold', color="#1B5E20")
    ax.text(19, 78.5, "• 拉普拉斯梯度方差計算 (Laplacian Variance)\n• 自動排除模糊失焦、曝光過度或全黑/白無效幀\n• 過濾非植物雜物，確保輸入信噪比", fontsize=9.5, color="#333333")
    
    rej1 = patches.FancyBboxPatch((19, 68), 32, 5, boxstyle="round,pad=0.3", ec="#C62828", fc="#FFEBEE", lw=1.2)
    ax.add_patch(rej1)
    ax.text(35, 70.5, "[攔截] 方差 < 5.0 (殘幀模糊) -> 直接拒絕推論，引導重拍", ha='center', va='center', fontsize=8.5, fontweight='bold', color="#C62828")

    ax.annotate("", xy=(55.5, 77), xytext=(53.5, 77), arrowprops=dict(arrowstyle="->", lw=2, color="#2E7D32"))
    ax.text(54.5, 79, "> 5.0 合格", ha='center', va='bottom', fontsize=8, fontweight='bold', color="#2E7D32")

    b2 = patches.FancyBboxPatch((56, 66.5), 41, 21, boxstyle="round,pad=0.5", ec="#1565C0", fc="#FFFFFF", lw=1.5)
    ax.add_patch(b2)
    ax.text(57.5, 84.5, "2. ConvNeXt 邊緣混合快篩 (Feature Gatekeeper)", fontsize=11, fontweight='bold', color="#0D47A1")
    ax.text(58, 77.5, "• Grad-CAM 前景注意力約束 (葉片對齊率 >= 35%)\n• 61 類動態特徵原型餘弦約束 (Cosine Sim >= 0.68)\n• 果實/葉片部位感知守門 + 輸出 Top-3 軟標籤候選", fontsize=9.5, color="#333333")

    # 分流箭頭
    ax.annotate("", xy=(68, 59.5), xytext=(68, 66), arrowprops=dict(arrowstyle="->", lw=2, color="#2E7D32"))
    ax.text(68, 62.8, "高置信/特徵對齊 (48%~56%)\n直接輸出 Top-3 進入主線 ->", ha='right', va='center', fontsize=8, fontweight='bold', color="#2E7D32")

    ax.annotate("", xy=(84, 59.5), xytext=(84, 66), arrowprops=dict(arrowstyle="->", lw=2, color="#E65100", linestyle="--"))
    ax.text(85, 62.8, "低置信/CAM脫靶 (<75%)\n轉交雲端兜底 ->", ha='left', va='center', fontsize=8, fontweight='bold', color="#E65100")

    # 階段 2
    p2 = patches.FancyBboxPatch((2, 34.5), 13, 24, boxstyle="round,pad=0.5", ec="#E65100", fc="#FFF3E0", lw=1.5)
    ax.add_patch(p2)
    ax.text(8.5, 46.5, "【第二階段】\n\n雲端雙軌\n專家會診與兜底\n\n[精準抗幻覺\n長尾高召回]", 
            ha='center', va='center', fontsize=10.5, fontweight='bold', color="#E65100")

    b3a = patches.FancyBboxPatch((17, 36), 38, 21, boxstyle="round,pad=0.5", ec="#2E7D32", fc="#FFFFFF", lw=1.5)
    ax.add_patch(b3a)
    ax.text(18.5, 53.5, "3A. Gemini 視覺覆核 (雙模型共識會診主線)", fontsize=11, fontweight='bold', color="#1B5E20")
    ax.text(19, 46.5, "• RAG 農業部標準病理特徵進行二次視覺比對\n• 雙重交叉檢驗：與端側 ConvNeXt 吻合 -> 達成共識確診\n• 特徵偏離/疑似幻覺 -> 專家標記爭議並即時推翻修正", fontsize=9.5, color="#333333")
    ax.text(36, 38.5, "[核心效益] 消除單一端側誤報，確診準確率躍升至 80.75%", ha='center', fontsize=8.5, fontweight='bold', color="#2E7D32")

    b3b = patches.FancyBboxPatch((58, 36), 39, 21, boxstyle="round,pad=0.5", ec="#E65100", fc="#FFFFFF", lw=1.5)
    ax.add_patch(b3b)
    ax.text(59.5, 53.5, "3B. Gemini 全局開集兜底 (罕見長尾病害)", fontsize=11, fontweight='bold', color="#BF360C")
    ax.text(60, 46.5, "• 廣域多模態視覺初判 (支援未收錄長尾罕見病害)\n• 官方白名單約束 + 非對稱置信度門檻 (65% / 85%)\n• 嚴密防止開放式多模態胡亂臆測日常觀賞花卉", fontsize=9.5, color="#333333")

    ood_box = patches.FancyBboxPatch((60, 38), 35, 5, boxstyle="round,pad=0.3", ec="#C62828", fc="#FFEBEE", lw=1.2)
    ax.add_patch(ood_box)
    ax.text(77.5, 40.5, "[攔截] 置信度 < 65% -> 觸發 OOD 安全防禦煞車 (回傳無法判定)", ha='center', va='center', fontsize=8, fontweight='bold', color="#C62828")

    ax.annotate("", xy=(36, 29.5), xytext=(36, 35.5), arrowprops=dict(arrowstyle="->", lw=2, color="#1B5E20"))
    ax.text(36, 32.5, "共識確診 ->", ha='center', va='center', fontsize=8, fontweight='bold', color="#1B5E20")

    ax.annotate("", xy=(68, 29.5), xytext=(68, 35.5), arrowprops=dict(arrowstyle="->", lw=2, color="#E65100"))
    ax.text(68, 32.5, ">= 65% 兜底確診 ->", ha='center', va='center', fontsize=8, fontweight='bold', color="#E65100")

    # 階段 3
    p3 = patches.FancyBboxPatch((2, 3), 13, 25, boxstyle="round,pad=0.5", ec="#4A148C", fc="#F3E5F5", lw=1.5)
    ax.add_patch(p3)
    ax.text(8.5, 15.5, "【第三階段】\n\n處方安全約束\n與時序閉環進化\n\n[工程落地實用\n零自創農藥]", 
            ha='center', va='center', fontsize=10.5, fontweight='bold', color="#4A148C")

    b4 = patches.FancyBboxPatch((17, 5), 38, 22, boxstyle="round,pad=0.5", ec="#4A148C", fc="#FFFFFF", lw=1.5)
    ax.add_patch(b4)
    ax.text(18.5, 23.5, "4. 官方精準處方拘束 (嚴禁 AI 自創未知農藥)", fontsize=11, fontweight='bold', color="#4A148C")
    ax.text(19, 17.5, "• 依病斑嚴重度動態開立專業防治建議\n• 嚴禁 LLM 自由發揮：處方完全鎖定官方審定庫", fontsize=9.5, color="#333333")
    
    p4a = patches.FancyBboxPatch((18.5, 11.5), 17, 4.5, boxstyle="round,pad=0.2", ec="#1B5E20", fc="#E8F5E9", lw=1)
    ax.add_patch(p4a)
    ax.text(27, 13.7, "4A. MySQL 官方庫 (優先匹配)", ha='center', va='center', fontsize=8, fontweight='bold', color="#1B5E20")

    p4b = patches.FancyBboxPatch((36.5, 11.5), 17, 4.5, boxstyle="round,pad=0.2", ec="#E65100", fc="#FFF3E0", lw=1)
    ax.add_patch(p4b)
    ax.text(45, 13.7, "4B. FAISS 植保專書 RAG 檢索", ha='center', va='center', fontsize=8, fontweight='bold', color="#E65100")

    ax.text(36, 7.5, "[防護] 徹底杜絕 Generative AI 憑空捏造無效或有害化學藥劑！", ha='center', fontsize=8.5, fontweight='bold', color="#C62828")

    b5 = patches.FancyBboxPatch((58, 5), 39, 22, boxstyle="round,pad=0.5", ec="#00695C", fc="#FFFFFF", lw=1.5)
    ax.add_patch(b5)
    ax.text(59.5, 23.5, "5. 邊緣時序防抖 & 主動學習進化閉環", fontsize=11, fontweight='bold', color="#004D40")
    ax.text(60, 17.5, "• Webcam 連續 3 幀穩定共識 (Confidence >= 80%)\n  時序平滑濾除環境光影與風吹晃動，誤判率降至 p³", fontsize=9.5, color="#333333")

    al_box = patches.FancyBboxPatch((59.5, 7), 36, 7.5, boxstyle="round,pad=0.3", ec="#00695C", fc="#E0F2F1", lw=1.2)
    ax.add_patch(al_box)
    ax.text(77.5, 12, "[主動學習閉環 Active Learning]", ha='center', va='center', fontsize=8.5, fontweight='bold', color="#004D40")
    ax.text(77.5, 9, "爭議樣本專家覆核 -> EMA 線上更新特徵原型 -> 反饋微調第 2 關 ConvNeXt", ha='center', va='center', fontsize=7.5, color="#004D40")

    # 閉環反向虛線箭頭回到第一階段 ConvNeXt
    ax.annotate("", xy=(97.5, 76), xytext=(97.5, 11), 
                arrowprops=dict(arrowstyle="->", lw=2, color="#00897B", linestyle=":", connectionstyle="arc3,rad=-0.12"))
    ax.text(98, 44, "EMA 動態微調反饋\n(持續適應田間多樣性)", ha='left', va='center', fontsize=8, fontweight='bold', color="#00897B")

    plt.tight_layout()
    out_png = ARTIFACTS_DIR / "presentation_redesign_option1_vertical_funnel.png"
    plt.savefig(out_png, dpi=300, facecolor=fig.get_facecolor(), edgecolor='none')
    plt.savefig(out_png.with_suffix('.svg'), format='svg')
    plt.close()
    print("Option 1 vertical funnel generated successfully!")


def generate_option2_slide_preview():
    """
    方案 2: 階段性分開 (3 頁漸進式投影片預覽總圖)
    向用戶展示如果拆成 3 張 PPT 頁面，每頁長什麼樣子，評審聽得最舒服
    """
    fig, axes = plt.subplots(1, 3, figsize=(18, 6.2), dpi=300)
    fig.patch.set_facecolor('#ECEFF1')

    titles = [
        "【投影片 1 / 3】\n第一階段：邊緣端前置品質與特徵守門",
        "【投影片 2 / 3】\n第二階段：雲端雙軌專家會診與長尾兜底",
        "【投影片 3 / 3】\n第三階段：官方處方拘束與邊緣閉環進化"
    ]

    colors = ["#2E7D32", "#E65100", "#4A148C"]
    bg_colors = ["#E8F5E9", "#FFF3E0", "#F3E5F5"]

    for i, ax in enumerate(axes):
        ax.set_xlim(0, 100)
        ax.set_ylim(0, 100)
        ax.axis('off')
        
        # 模擬 16:9 投影片白底卡片
        slide_card = patches.FancyBboxPatch((1, 1), 98, 98, boxstyle="round,pad=1", ec="#B0BEC5", fc="#FFFFFF", lw=2)
        ax.add_patch(slide_card)

        # 頂部彩色 Banner
        banner = patches.FancyBboxPatch((2, 85), 96, 13, boxstyle="round,pad=0.5", ec=colors[i], fc=bg_colors[i], lw=1.5)
        ax.add_patch(banner)
        ax.text(50, 91.5, titles[i], ha='center', va='center', fontsize=11, fontweight='bold', color=colors[i])

    # --- 投影片 1 內容 ---
    ax1 = axes[0]
    c1 = patches.FancyBboxPatch((6, 54), 88, 27, boxstyle="round,pad=0.5", ec="#2E7D32", fc="#F1F8E9", lw=1.2)
    ax1.add_patch(c1)
    ax1.text(8, 76, "關卡 1. 影像品質快篩 (Laplacian Variance)", fontsize=10.5, fontweight='bold', color="#1B5E20")
    ax1.text(10, 68, "• 方差計算排除模糊、失焦、黑屏與反光過曝\n• 攔截殘幀：方差 < 5.0 拒絕推論，引導補拍\n• 效益：防止垃圾資料污染後續推論鏈", fontsize=9, color="#333333")

    c2 = patches.FancyBboxPatch((6, 18), 88, 32, boxstyle="round,pad=0.5", ec="#1565C0", fc="#E3F2FD", lw=1.2)
    ax1.add_patch(c2)
    ax1.text(8, 44, "關卡 2. ConvNeXt 邊緣混合快篩 (Edge Gatekeeper)", fontsize=10.5, fontweight='bold', color="#0D47A1")
    ax1.text(10, 32, "• Grad-CAM 注意力約束 (前景葉片佔比 >= 35%)\n• 61 類動態特徵原型餘弦相似度 (Cosine >= 0.68)\n• 部位感知守門 + 輸出 Top-3 軟標籤候選", fontsize=9, color="#333333")
    ax1.text(50, 23, "【報告要點】在手機/樹莓派本機僅花 4ms，\n直接搞定 50%+ 明確病害，大幅降低雲端費用！", 
             ha='center', fontsize=8.5, fontweight='bold', color="#0D47A1", bbox=dict(boxstyle="round,pad=0.3", fc="#BBDEFB", ec="#1976D2", lw=1))

    # --- 投影片 2 內容 ---
    ax2 = axes[1]
    c3a = patches.FancyBboxPatch((6, 52), 88, 29, boxstyle="round,pad=0.5", ec="#2E7D32", fc="#E8F5E9", lw=1.2)
    ax2.add_patch(c3a)
    ax2.text(8, 76, "關卡 3A. Gemini 視覺覆核 (雙模型共識主線)", fontsize=10.5, fontweight='bold', color="#1B5E20")
    ax2.text(10, 66, "• 依端側 Top-3 檢索 RAG 農業部標準病理特徵\n• 與 ConvNeXt 達成共識即確診 (準確率達 80.75%)\n• 特徵衝突時：推翻修正並記錄標記爭議", fontsize=9, color="#333333")

    c3b = patches.FancyBboxPatch((6, 18), 88, 30, boxstyle="round,pad=0.5", ec="#E65100", fc="#FFF3E0", lw=1.2)
    ax2.add_patch(c3b)
    ax2.text(8, 43, "關卡 3B. Gemini 全局開集兜底 (罕見長尾病害)", fontsize=10.5, fontweight='bold', color="#BF360C")
    ax2.text(10, 33, "• 支援端側未收錄之長尾開集植物病害\n• 白名單約束 + 非對稱門檻 (65% / 85%)\n• OOD 安全煞車：置信度 < 65% 主動拒答防幻覺", fontsize=9, color="#333333")
    ax2.text(50, 23, "【報告要點】絕不讓 LLM 盲猜！雙軌分流保證\n常用病害雙重覆核，長尾罕見病害安全兜底！", 
             ha='center', fontsize=8.5, fontweight='bold', color="#BF360C", bbox=dict(boxstyle="round,pad=0.3", fc="#FFE0B2", ec="#F57C00", lw=1))

    # --- 投影片 3 內容 ---
    ax3 = axes[2]
    c4 = patches.FancyBboxPatch((6, 52), 88, 29, boxstyle="round,pad=0.5", ec="#4A148C", fc="#F3E5F5", lw=1.2)
    ax3.add_patch(c4)
    ax3.text(8, 76, "關卡 4. 雙重官方處方拘束 (嚴禁 AI 自創農藥)", fontsize=10.5, fontweight='bold', color="#4A148C")
    ax3.text(10, 66, "• 依病斑嚴重度開立官方審定用藥與物理防治\n• 4A. MySQL 官方庫直接精準對應客定指引\n• 4B. 未收錄病害透過 FAISS 檢索植保專書限制處方", fontsize=9, color="#333333")

    c5 = patches.FancyBboxPatch((6, 18), 88, 30, boxstyle="round,pad=0.5", ec="#00695C", fc="#E0F2F1", lw=1.2)
    ax3.add_patch(c5)
    ax3.text(8, 43, "關卡 5 & 閉環. Webcam 防抖 + 主動學習進化", fontsize=10.5, fontweight='bold', color="#004D40")
    ax3.text(10, 33, "• Webcam 連續 3 幀共識 (>=80%)，誤報率降至 p³\n• 爭議標本自動觸發專家覆核標記\n• EMA 線上動態更新特徵原型，持續進化微調 ConvNeXt", fontsize=9, color="#333333")
    ax3.text(50, 23, "【報告要點】實體落地最關鍵！保證不開假藥，\n即時鏡頭不閃爍，且具備自我演進能力！", 
             ha='center', fontsize=8.5, fontweight='bold', color="#004D40", bbox=dict(boxstyle="round,pad=0.3", fc="#B2DFDB", ec="#00897B", lw=1))

    plt.tight_layout()
    out_png = ARTIFACTS_DIR / "presentation_redesign_option2_slide_deck_preview.png"
    plt.savefig(out_png, dpi=300, facecolor=fig.get_facecolor(), edgecolor='none')
    plt.savefig(out_png.with_suffix('.svg'), format='svg')
    plt.close()
    print("Option 2 slide deck preview generated successfully!")

if __name__ == "__main__":
    generate_option1()
    generate_option2_slide_preview()
