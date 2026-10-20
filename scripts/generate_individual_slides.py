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

def create_slide_base(title_text, subtitle_text, stage_tag, stage_color):
    fig, ax = plt.subplots(figsize=(16, 9), dpi=300)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis('off')
    fig.patch.set_facecolor('#F8F9FA')

    # 頂部導航進度條
    stages = ["第一階段: 邊緣守門", "第二階段: 雲端會診", "第三階段: 處方與閉環"]
    for idx, s_name in enumerate(stages):
        x = 6 + idx * 30
        is_cur = (stage_tag == f"階段 {idx+1}")
        col = stage_color if is_cur else "#B0BEC5"
        txt_col = "#FFFFFF" if is_cur else "#546E7A"
        bg_p = patches.FancyBboxPatch((x, 92), 28, 5, boxstyle="round,pad=0.3", ec=col, fc=col if is_cur else "#ECEFF1", lw=1.2)
        ax.add_patch(bg_p)
        ax.text(x + 14, 94.5, s_name, ha='center', va='center', fontsize=11, fontweight='bold', color=txt_col)

    # 標題
    ax.text(6, 85, title_text, fontsize=20, fontweight='bold', color='#1A237E')
    ax.text(6, 80, subtitle_text, fontsize=12, color='#555555')
    return fig, ax

def generate_slide_1():
    fig, ax = create_slide_base(
        "【第一階段】邊緣端前置：品質過濾與特徵空間守門",
        "核心目標：本機 4ms 極速快篩排除無效雜訊，攔截 50%+ 請求免調用雲端 API",
        "階段 1", "#2E7D32"
    )

    # 關卡 1 卡片 (左側)
    c1 = patches.FancyBboxPatch((6, 12), 42, 63, boxstyle="round,pad=0.8", ec="#2E7D32", fc="#FFFFFF", lw=2)
    ax.add_patch(c1)
    # Banner
    b1 = patches.FancyBboxPatch((7, 66), 40, 7.5, boxstyle="round,pad=0.4", ec="#2E7D32", fc="#E8F5E9", lw=1.2)
    ax.add_patch(b1)
    ax.text(27, 69.8, "關卡 1. 影像品質快篩 (Input Filter)", ha='center', va='center', fontsize=14, fontweight='bold', color="#1B5E20")

    ax.text(8.5, 59, "【技術原理與過濾策略】", fontsize=12, fontweight='bold', color="#2E7D32")
    ax.text(8.5, 47, "• 拉普拉斯梯度方差 (Laplacian Variance)：\n  即時評估影像銳利度與邊緣梯度能量\n• 自動排除過度晃動模糊、失焦、黑屏或曝光過度\n• 過濾非植物雜物，確保後續特徵純度", fontsize=11, color="#333333")

    rej_card = patches.FancyBboxPatch((8.5, 28), 37, 14, boxstyle="round,pad=0.5", ec="#C62828", fc="#FFEBEE", lw=1.5)
    ax.add_patch(rej_card)
    ax.text(27, 37.5, "[嚴格防護 1：殘幀攔截煞車]", ha='center', va='center', fontsize=12, fontweight='bold', color="#C62828")
    ax.text(27, 32.5, "方差 < 5.0 (模糊無效幀) -> 拒絕進入推論！\n直接提示使用者『鏡頭晃動，請重新對焦拍照』", ha='center', va='center', fontsize=10.5, color="#C62828")

    # 關卡 2 卡片 (右側)
    c2 = patches.FancyBboxPatch((52, 12), 42, 63, boxstyle="round,pad=0.8", ec="#1565C0", fc="#FFFFFF", lw=2)
    ax.add_patch(c2)
    b2 = patches.FancyBboxPatch((53, 66), 40, 7.5, boxstyle="round,pad=0.4", ec="#1565C0", fc="#E3F2FD", lw=1.2)
    ax.add_patch(b2)
    ax.text(73, 69.8, "關卡 2. ConvNeXt 混合快篩 (Feature Gatekeeper)", ha='center', va='center', fontsize=14, fontweight='bold', color="#0D47A1")

    ax.text(54.5, 59, "【三重視覺幾何與特徵約束】", fontsize=12, fontweight='bold', color="#0D47A1")
    ax.text(54.5, 45, "1. Grad-CAM 前景注意力約束 (葉片對齊率 >= 35%)\n   避免模型將雜草或手掌背景誤判為病害\n2. 61 類動態特徵原型餘弦約束 (Cosine Sim >= 0.68)\n   確保特徵向量落入該類別高密度分佈區\n3. 果實/葉片部位感知守門 + 輸出 Top-3 軟標籤", fontsize=11, color="#333333")

    decision_card = patches.FancyBboxPatch((54.5, 26), 37, 16, boxstyle="round,pad=0.5", ec="#0D47A1", fc="#E8EAF6", lw=1.5)
    ax.add_patch(decision_card)
    ax.text(73, 37.5, "[分流決策結果 (4ms 本地完成)]", ha='center', va='center', fontsize=12, fontweight='bold', color="#0D47A1")
    ax.text(73, 31, "• 高置信且特徵對齊 (48%~56% 請求) -> 直接輸出！\n• 信心不足或 CAM 脫靶 -> 轉交雲端雙軌會診", ha='center', va='center', fontsize=10.5, color="#1A237E")

    plt.tight_layout()
    out_png = ARTIFACTS_DIR / "presentation_option2_slide1_edge.png"
    plt.savefig(out_png, dpi=300, facecolor=fig.get_facecolor(), edgecolor='none')
    plt.savefig(out_png.with_suffix('.svg'), format='svg')
    plt.close()
    print("Slide 1 generated successfully!")

def generate_slide_2():
    fig, ax = create_slide_base(
        "【第二階段】雲端雙軌專家會診與罕見病害兜底",
        "核心目標：絕不讓通用 LLM 盲猜！雙軌分流保證常見病害雙重覆核，罕見病害安全兜底",
        "階段 2", "#E65100"
    )

    # 3A 雙模型會診
    c1 = patches.FancyBboxPatch((6, 12), 42, 63, boxstyle="round,pad=0.8", ec="#2E7D32", fc="#FFFFFF", lw=2)
    ax.add_patch(c1)
    b1 = patches.FancyBboxPatch((7, 66), 40, 7.5, boxstyle="round,pad=0.4", ec="#2E7D32", fc="#E8F5E9", lw=1.2)
    ax.add_patch(b1)
    ax.text(27, 69.8, "3A. Gemini 視覺覆核 (雙模型共識主線)", ha='center', va='center', fontsize=14, fontweight='bold', color="#1B5E20")

    ax.text(8.5, 59, "【雙模型交叉驗證機制】", fontsize=12, fontweight='bold', color="#2E7D32")
    ax.text(8.5, 47, "• 接收端側 Top-3 候選軟標籤，縮小搜尋空間\n• RAG 農業部標準病理特徵庫進行二次特徵比對\n• 雙重交叉檢驗：\n  - 吻合端側預測 -> 達成共識確診 (準確率 75.75%)\n  - 特徵嚴重偏差 -> 專家推翻修正，防止單模型誤判", fontsize=11, color="#333333")

    c1_stat = patches.FancyBboxPatch((8.5, 25), 37, 17, boxstyle="round,pad=0.5", ec="#2E7D32", fc="#F1F8E9", lw=1.5)
    ax.add_patch(c1_stat)
    ax.text(27, 36.5, "[實測數據驗證]", ha='center', va='center', fontsize=12, fontweight='bold', color="#1B5E20")
    ax.text(27, 30, "在端側轉交的 176 張極限疑難樣本中：\nGemini 3.8 正向救回多數題目，淨貢獻 +36 題！\n整體準確率從 66.75% 提升至 75.75%", ha='center', va='center', fontsize=10.5, color="#1B5E20")

    ax.text(27, 16, "效益：雙重覆核機制，消除單一模型之固有盲區！", ha='center', fontsize=11, fontweight='bold', color="#2E7D32")

    # 3B 罕見病害開集兜底
    c2 = patches.FancyBboxPatch((52, 12), 42, 63, boxstyle="round,pad=0.8", ec="#E65100", fc="#FFFFFF", lw=2)
    ax.add_patch(c2)
    b2 = patches.FancyBboxPatch((53, 66), 40, 7.5, boxstyle="round,pad=0.4", ec="#E65100", fc="#FFF3E0", lw=1.2)
    ax.add_patch(b2)
    ax.text(73, 69.8, "3B. Gemini 全局開集兜底 (罕見病害)", ha='center', va='center', fontsize=14, fontweight='bold', color="#BF360C")

    ax.text(54.5, 59, "【罕見病害召回與防幻覺煞車】", fontsize=12, fontweight='bold', color="#BF360C")
    ax.text(54.5, 47, "• 當端側完全無法匹配時，啟動廣域多模態初判\n• 開集識別兜底：支援本地模型 61 類清單之外的罕見植物病害\n• 官方農業白名單約束 (嚴禁胡亂臆測觀賞花卉)\n• 非對稱動態門檻 (已知病害 65% / 罕見病害 85%)", fontsize=11, color="#333333")

    ood_card = patches.FancyBboxPatch((54.5, 25), 37, 17, boxstyle="round,pad=0.5", ec="#C62828", fc="#FFEBEE", lw=1.5)
    ax.add_patch(ood_card)
    ax.text(73, 36.5, "[嚴格防護 2：OOD 安全防禦煞車]", ha='center', va='center', fontsize=12, fontweight='bold', color="#C62828")
    ax.text(73, 30, "置信度 < 65% (極端分佈外樣本) ->\n系統主動回傳『無法判定』並煞車！\n寧可誠實拒答，絕不胡亂猜測誤導農民", ha='center', va='center', fontsize=10.5, color="#C62828")

    ax.text(73, 16, "效益：罕見病害高召回率 + OOD 拒答雙重平衡！", ha='center', fontsize=11, fontweight='bold', color="#BF360C")

    plt.tight_layout()
    out_png = ARTIFACTS_DIR / "presentation_option2_slide2_cloud.png"
    plt.savefig(out_png, dpi=300, facecolor=fig.get_facecolor(), edgecolor='none')
    plt.savefig(out_png.with_suffix('.svg'), format='svg')
    plt.close()
    print("Slide 2 generated successfully!")

def generate_slide_3():
    fig, ax = create_slide_base(
        "【第三階段】官方處方安全約束與邊緣閉環進化",
        "核心目標：杜絕 AI 自創假農藥，保證現場鏡頭即時穩定，並具備自我反饋進化能力",
        "階段 3", "#4A148C"
    )

    # 4 雙重處方拘束
    c1 = patches.FancyBboxPatch((6, 12), 42, 63, boxstyle="round,pad=0.8", ec="#4A148C", fc="#FFFFFF", lw=2)
    ax.add_patch(c1)
    b1 = patches.FancyBboxPatch((7, 66), 40, 7.5, boxstyle="round,pad=0.4", ec="#4A148C", fc="#F3E5F5", lw=1.2)
    ax.add_patch(b1)
    ax.text(27, 69.8, "關卡 4. 雙重官方處方拘束 (嚴禁自創農藥)", ha='center', va='center', fontsize=14, fontweight='bold', color="#4A148C")

    ax.text(8.5, 59, "【雙軌處方強制對齊機制】", fontsize=12, fontweight='bold', color="#4A148C")
    ax.text(8.5, 47, "• 依病斑嚴重程度 (輕度/中度/重度) 動態調整指引\n• 嚴禁 LLM 自由發揮藥名，處方完全來自審定庫：", fontsize=11, color="#333333")

    # 4A
    p4a = patches.FancyBboxPatch((8.5, 36), 37, 8.5, boxstyle="round,pad=0.4", ec="#1B5E20", fc="#E8F5E9", lw=1.2)
    ax.add_patch(p4a)
    ax.text(27, 41.5, "4A. 農業部官方資料庫 (MySQL 優先查庫)", ha='center', va='center', fontsize=11, fontweight='bold', color="#1B5E20")
    ax.text(27, 38, "介接防檢署 (APHIA) 與開放資料，匹配核定用藥與稀釋比例", ha='center', va='center', fontsize=9.2, color="#333333")

    # 4B
    p4b = patches.FancyBboxPatch((8.5, 23.2), 37, 10.3, boxstyle="round,pad=0.4", ec="#E65100", fc="#FFF3E0", lw=1.2)
    ax.add_patch(p4b)
    ax.text(27, 31.0, "4B. 農業部植保專書 (FAISS RAG 檢索)", ha='center', va='center', fontsize=11, fontweight='bold', color="#E65100")
    ax.text(27, 28.0, "向量鎖定《植保手冊》與《害蟲圖鑑》專書，拘束生成", ha='center', va='center', fontsize=9.2, color="#333333")
    ax.text(27, 25.2, "※ 若前述皆未收錄，自動退避由 Gemini 多模態原生知識兜底", ha='center', va='center', fontsize=8.5, color="#D84315")

    ax.text(27, 16, "效益：100% 避免因 LLM 幻覺造成農民藥害與違法！", ha='center', fontsize=11, fontweight='bold', color="#C62828")

    # 右側上方塊：關卡 5 時序防抖
    c2_top = patches.FancyBboxPatch((52, 44.5), 42, 30.5, boxstyle="round,pad=0.8", ec="#00695C", fc="#FFFFFF", lw=2)
    ax.add_patch(c2_top)
    b2_top = patches.FancyBboxPatch((53, 68), 40, 6.5, boxstyle="round,pad=0.4", ec="#00695C", fc="#E0F2F1", lw=1.2)
    ax.add_patch(b2_top)
    ax.text(73, 71.2, "關卡 5. Webcam 時序防抖穩定共識", ha='center', va='center', fontsize=13, fontweight='bold', color="#004D40")

    ax.text(54.5, 63.5, "【連續幀平滑過濾 (>= 80% 門檻)】", fontsize=11, fontweight='bold', color="#004D40")
    ax.text(54.5, 54.5, "• Webcam 連續 3 幀預測一致且信心度 >= 80% 方觸發確診\n• 時序平滑濾除光影變化與風吹晃動，誤報率降至 p³ (51%)\n• 避免現場實機展示畫面頻繁跳閃，保證視覺穩定輸出", fontsize=10, color="#333333")
    ax.text(73, 47, "效益：消除實機展示跳閃，大幅壓低鏡頭晃動誤報！", ha='center', va='center', fontsize=10, fontweight='bold', color="#00695C")

    # 右側下方塊：系統閉環 主動學習進化
    c2_bot = patches.FancyBboxPatch((52, 12), 42, 30.5, boxstyle="round,pad=0.8", ec="#00897B", fc="#FFFFFF", lw=2)
    ax.add_patch(c2_bot)
    b2_bot = patches.FancyBboxPatch((53, 35.5), 40, 6.5, boxstyle="round,pad=0.4", ec="#00897B", fc="#E0F2F1", lw=1.2)
    ax.add_patch(b2_bot)
    ax.text(73, 38.7, "閉環. 主動學習自適應進化 (Active Learning)", ha='center', va='center', fontsize=13, fontweight='bold', color="#004D40")

    ax.text(54.5, 31, "【特徵原型線上更新與持續回饋】", fontsize=11, fontweight='bold', color="#004D40")
    ax.text(54.5, 22.5, "• 雲端爭議案例自動標記審查，專家在線覆核標註\n• 驗證樣本以 EMA (指數移動平均) 線上即時更新特徵原型\n• 定期反向微調第 2 關本地 ConvNeXt，系統越用越聰明！", fontsize=10, color="#333333")
    ax.text(73, 15, "效益：建立數據飛輪閉環，讓邊緣模型持續自我演進！", ha='center', va='center', fontsize=10, fontweight='bold', color="#004D40")

    plt.tight_layout()
    out_png = ARTIFACTS_DIR / "presentation_option2_slide3_action.png"
    plt.savefig(out_png, dpi=300, facecolor=fig.get_facecolor(), edgecolor='none')
    plt.savefig(out_png.with_suffix('.svg'), format='svg')
    plt.close()
    print("Slide 3 generated successfully!")

if __name__ == "__main__":
    generate_slide_1()
    generate_slide_2()
    generate_slide_3()
