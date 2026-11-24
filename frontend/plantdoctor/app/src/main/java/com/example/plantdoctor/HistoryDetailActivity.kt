package com.example.plantdoctor

import android.content.Context
import android.content.Intent
import android.graphics.Color
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.view.MotionEvent
import android.view.View
import android.widget.LinearLayout
import android.widget.Button
import android.widget.EditText
import android.widget.ImageButton
import android.widget.ImageView
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.cardview.widget.CardView
import androidx.coordinatorlayout.widget.CoordinatorLayout
import com.bumptech.glide.Glide
import com.getkeepsafe.taptargetview.TapTarget
import com.getkeepsafe.taptargetview.TapTargetView
import com.google.android.material.bottomsheet.BottomSheetBehavior
import retrofit2.Call
import retrofit2.Callback
import retrofit2.Response
import java.util.Date
import java.util.Locale

class HistoryDetailActivity : AppCompatActivity() {

    private var diaryId: Int = -1
    private var currentImageUrl: String? = null

    private lateinit var imgPlant: ImageView
    private lateinit var imgPipPlant: ImageView
    private lateinit var tvPlantName: TextView
    private lateinit var tvDiseaseName: TextView
    private lateinit var tvAdvice: TextView
    private lateinit var btnAction: Button
    private lateinit var btnBack: ImageButton
    private lateinit var tvMainTitle: TextView

    private lateinit var historyRoot: CoordinatorLayout
    private lateinit var cvImageContainer: CardView
    private lateinit var cvPipContainer: CardView
    private lateinit var cardAdvice: CardView

    // 使用者筆記 UI 元件
    private lateinit var layoutNoteDisplay: LinearLayout
    private lateinit var layoutNoteEdit: LinearLayout
    private lateinit var tvUserNoteDisplay: TextView
    private lateinit var etUserNoteEdit: EditText
    private lateinit var ivEditNote: ImageView
    private lateinit var btnSaveNote: Button

    // 🌟 時間軸與康復追蹤相關 UI 元件
    private lateinit var tvTimelineHeaderTitle: TextView
    private lateinit var tvTrendTitle: TextView
    private lateinit var tvTrendDesc: TextView
    private lateinit var tvCompareTitle: TextView
    private lateinit var layoutBeforeAfter: LinearLayout
    private lateinit var imgBefore: ImageView
    private lateinit var tvBeforeLabel: TextView
    private lateinit var tvBeforeDate: TextView
    private lateinit var imgAfter: ImageView
    private lateinit var tvAfterLabel: TextView
    private lateinit var tvAfterDate: TextView
    private lateinit var cvBeforeImg: CardView
    private lateinit var cvAfterImg: CardView
    private lateinit var containerTimelineNodes: LinearLayout

    // 🌟 專家處方箋區塊化與一鍵打卡元件
    private lateinit var tvDetailSymptom: TextView
    private lateinit var tvDetailTreatment: TextView
    private lateinit var btnOpenRemedyCatalog: TextView
    private lateinit var btnCareCheckin: TextView

    private var dX = 0f
    private var dY = 0f
    private var startX = 0f
    private var startY = 0f
    private var isDragging = false // 🌟 防止托曳誤觸放大
    private var isFirstTimeDetail = false
    var startStep2: (() -> Unit)? = null // 用於連鎖觸發

    private val windHandler = Handler(Looper.getMainLooper())
    private val windRunnable = Runnable {
        SoundManager.startWind()
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_history_detail)

        diaryId = intent.getIntExtra("DIARY_ID", -1)

        initViews()
        setupLogic()
        fetchData()
        //setupHistoryDetailGuide()
    }

    private fun initViews() {
        historyRoot = findViewById(R.id.history_detail_root_layout)
        tvMainTitle = findViewById(R.id.tv_title)
        imgPlant = findViewById(R.id.img_result_plant)
        imgPipPlant = findViewById(R.id.img_pip_plant)
        tvPlantName = findViewById(R.id.tv_plant_name)
        tvDiseaseName = findViewById(R.id.tv_disease_name)
        tvAdvice = findViewById(R.id.tv_advice)
        btnAction = findViewById(R.id.btn_save_report)
        btnBack = findViewById(R.id.btn_back_home)

        cvImageContainer = findViewById(R.id.cv_image_container)
        cvPipContainer = findViewById(R.id.cv_pip_container)
        cardAdvice = findViewById(R.id.card_advice)

        // 綁定使用者筆記元件
        layoutNoteDisplay = findViewById(R.id.layout_note_display)
        layoutNoteEdit = findViewById(R.id.layout_note_edit)
        tvUserNoteDisplay = findViewById(R.id.tv_user_note_display)
        etUserNoteEdit = findViewById(R.id.et_user_note_edit)
        ivEditNote = findViewById(R.id.iv_edit_note)
        btnSaveNote = findViewById(R.id.btn_save_note)

        // 🌟 綁定生長與康復時間軸元件
        tvTimelineHeaderTitle = findViewById(R.id.tv_timeline_header_title)
        tvTrendTitle = findViewById(R.id.tv_trend_title)
        tvTrendDesc = findViewById(R.id.tv_trend_desc)
        tvCompareTitle = findViewById(R.id.tv_compare_title)
        layoutBeforeAfter = findViewById(R.id.layout_before_after)
        imgBefore = findViewById(R.id.img_before)
        tvBeforeLabel = findViewById(R.id.tv_before_label)
        tvBeforeDate = findViewById(R.id.tv_before_date)
        imgAfter = findViewById(R.id.img_after)
        tvAfterLabel = findViewById(R.id.tv_after_label)
        tvAfterDate = findViewById(R.id.tv_after_date)
        cvBeforeImg = findViewById(R.id.cv_before_img)
        cvAfterImg = findViewById(R.id.cv_after_img)
        containerTimelineNodes = findViewById(R.id.container_timeline_nodes)

        // 🌟 綁定處方箋區塊化與打卡按鈕
        tvDetailSymptom = findViewById(R.id.tv_detail_symptom)
        tvDetailTreatment = findViewById(R.id.tv_detail_treatment)
        btnOpenRemedyCatalog = findViewById(R.id.btn_open_remedy_catalog)
        btnCareCheckin = findViewById(R.id.btn_care_checkin)

        // 限制卡片最高只能滑到「病例詳情」標題的下方
        val behavior = BottomSheetBehavior.from(cardAdvice)
        tvMainTitle.post {
            val titleBottom = tvMainTitle.bottom
            val marginPx = (16 * resources.displayMetrics.density).toInt()
            behavior.expandedOffset = titleBottom + marginPx
        }

        // 🌟 找到你程式碼中的 behavior.addBottomSheetCallback，將其內容修改如下：

        behavior.addBottomSheetCallback(object : BottomSheetBehavior.BottomSheetCallback() {
            override fun onStateChanged(bottomSheet: View, newState: Int) {
                if (newState == BottomSheetBehavior.STATE_EXPANDED) {
                    cvPipContainer.visibility = View.VISIBLE
                    cvPipContainer.alpha = 1f

                    // 🌟 新增：當偵測到卡片確實展開完成，立刻觸發第二步指引！
                    if (isFirstTimeDetail) {
                        startStep2?.invoke()
                        startStep2 = null // 避免重複觸發
                    }
                } else if (newState == BottomSheetBehavior.STATE_COLLAPSED) {
                    cvPipContainer.visibility = View.GONE
                }
            }

            override fun onSlide(bottomSheet: View, slideOffset: Float) {
                if (slideOffset > 0.8f) {
                    cvPipContainer.visibility = View.VISIBLE
                    cvPipContainer.alpha = (slideOffset - 0.8f) * 5f
                } else {
                    cvPipContainer.visibility = View.GONE
                }
            }
        })

        setupPipDragListener()

        ThemeManager.applyTheme(
            context = this,
            rootLayout = historyRoot,
            titles = listOf(tvMainTitle),
            imageButtons = listOf(btnBack)
        )
    }

    private fun setupLogic() {
        btnAction.text = "刪除此筆病例"
        btnAction.backgroundTintList = getColorStateList(android.R.color.holo_red_light)

        // 🌟 修改：點擊刪除按鈕時，改為跳出客製化刪除確認對話框
        btnAction.setOnClickListener {
            SoundManager.playBubblePop()
            showDeleteConfirmationDialog()
        }

        btnBack.setOnClickListener {
            SoundManager.playBubblePop()
            finish()
        }

        imgPlant.setOnClickListener { openImagePreview() }
        cvPipContainer.setOnClickListener { openImagePreview() }

        ivEditNote.setOnClickListener { switchToEditMode() }
        btnSaveNote.setOnClickListener { handleSaveNote() }
    }

    private fun openImagePreview() {
        if (!currentImageUrl.isNullOrEmpty()) {
            SoundManager.playBubblePop()
            val intent = Intent(this, ImagePreviewActivity::class.java).apply {
                putExtra("IMAGE_PATH", currentImageUrl)
            }
            startActivity(intent)
        }
    }

    // 🌟 核心調整：徹底解決滑動誤觸放大問題，並限制最高拖曳區塊，防止與診斷報告內容疊加
    private fun setupPipDragListener() {
        cvPipContainer.setOnTouchListener { view, event ->
            when (event.action) {
                MotionEvent.ACTION_DOWN -> {
                    startX = event.rawX
                    startY = event.rawY
                    dX = view.x - event.rawX
                    dY = view.y - event.rawY
                    isDragging = false
                    windHandler.postDelayed(windRunnable, 500)
                }
                MotionEvent.ACTION_MOVE -> {
                    val distanceX = event.rawX - startX
                    val distanceY = event.rawY - startY

                    if (Math.abs(distanceX) > 10 || Math.abs(distanceY) > 10) {
                        isDragging = true
                    }

                    if (isDragging) {
                        var newX = event.rawX + dX
                        var newY = event.rawY + dY

                        val maxContainerX = historyRoot.width - view.width
                        val maxContainerY = historyRoot.height - view.height

                        // 🌟 調整這裡：限制最高只能到診斷卡片頂端再往下 35dp (避免卡片完全展開時它跑太高)
                        val safetyMargin = (35 * resources.displayMetrics.density).toInt()
                        val minYLimit = cardAdvice.top.toFloat() + safetyMargin

                        newX = Math.max(0f, Math.min(newX, maxContainerX.toFloat()))
                        newY = Math.max(minYLimit, Math.min(newY, maxContainerY.toFloat()))

                        view.x = newX
                        view.y = newY
                    }
                }
                MotionEvent.ACTION_UP, MotionEvent.ACTION_CANCEL -> {
                    windHandler.removeCallbacks(windRunnable)
                    SoundManager.stopWind()

                    if (!isDragging) {
                        view.performClick()
                    }
                }
            }
            true
        }
    }

    private fun switchToDisplayMode() {
        layoutNoteDisplay.visibility = View.VISIBLE
        layoutNoteEdit.visibility = View.GONE
    }

    private fun switchToEditMode() {
        layoutNoteDisplay.visibility = View.GONE
        layoutNoteEdit.visibility = View.VISIBLE
        etUserNoteEdit.setText(tvUserNoteDisplay.text)
        etUserNoteEdit.setSelection(etUserNoteEdit.text.length)
    }

    private fun handleSaveNote() {
        val updatedNote = etUserNoteEdit.text.toString()
        saveNoteToServer(updatedNote)
    }

    private fun handleCareCheckin(isHealthy: Boolean) {
        val todayStr = java.text.SimpleDateFormat("yyyy-MM-dd HH:mm", Locale.getDefault()).format(Date())
        val checkinText = if (isHealthy) {
            "【💧 照護打卡】$todayStr 已完成日常澆水與生長環境通風巡檢。"
        } else {
            "【🌿 照護打卡】$todayStr 已依處方指南完成藥劑噴灑與通風照護。"
        }

        val existingNote = tvUserNoteDisplay.text.toString().trim()
        val finalNote = if (existingNote.isBlank() || existingNote.contains("點選右側鉛筆")) {
            checkinText
        } else {
            "$existingNote\n$checkinText"
        }

        val successMsg = if (isHealthy) {
            "打卡成功！已為此植物累積一次日常生長澆水紀錄 🌱"
        } else {
            "打卡成功！已為此植物累積一次康復照護紀錄 🎉"
        }

        saveNoteToServer(finalNote) {
            Toast.makeText(this, successMsg, Toast.LENGTH_LONG).show()
            // 重新刷新時間軸
            fetchTimelineData()
        }
    }

    private fun saveNoteToServer(updatedNote: String, onSuccess: (() -> Unit)? = null) {
        btnSaveNote.isEnabled = false

        val sharedPref = getSharedPreferences("PlantDoctor", Context.MODE_PRIVATE)
        val token = sharedPref.getString("token", "") ?: ""
        val request = PatchDiaryRequest(user_note = updatedNote)

        PlantApiService.create(token).patchDiary(diaryId, request).enqueue(object : Callback<GenericResponse> {
            override fun onResponse(call: Call<GenericResponse>, response: Response<GenericResponse>) {
                btnSaveNote.isEnabled = true
                if (response.isSuccessful) {
                    Toast.makeText(this@HistoryDetailActivity, "筆記已儲存", Toast.LENGTH_SHORT).show()
                    tvUserNoteDisplay.text = updatedNote
                    switchToDisplayMode()
                    onSuccess?.invoke()
                } else {
                    Toast.makeText(this@HistoryDetailActivity, "儲存失敗: ${response.code()}", Toast.LENGTH_SHORT).show()
                }
            }
            override fun onFailure(call: Call<GenericResponse>, t: Throwable) {
                btnSaveNote.isEnabled = true
                Toast.makeText(this@HistoryDetailActivity, "儲存失敗: 網路問題", Toast.LENGTH_SHORT).show()
            }
        })
    }

    private fun setupHistoryDetailGuide() {
        val sharedPref = getSharedPreferences("PlantDoctor", Context.MODE_PRIVATE)
        isFirstTimeDetail = sharedPref.getBoolean("IS_FIRST_TIME_HISTORY_DETAIL", true)

        if (isFirstTimeDetail) {
            val targetColorRes = android.R.color.holo_green_dark
            val autoJumpHandler = Handler(Looper.getMainLooper())
            val behavior = BottomSheetBehavior.from(cardAdvice)

            var targetView1: TapTargetView? = null
            var targetView2: TapTargetView? = null
            var targetView3: TapTargetView? = null

            // 🌟 核心狀態鎖：防止連點、防分身重複觸發
            var currentStep = 1

            val jumpToStep2Runnable = Runnable { targetView1?.dismiss(true) }
            val jumpToStep3Runnable = Runnable { targetView2?.dismiss(true) }
            val finishGuideRunnable = Runnable { targetView3?.dismiss(true) }

            // 3️⃣ 第三步：懸浮窗小圖
            val startStep3 = {
                if (currentStep == 3) { // 確保只執行一次
                    SoundManager.playBubblePop()
                    targetView3 = TapTargetView.showFor(this,
                        TapTarget.forView(cvPipContainer, "小窗隨身看", "展開報告後，照片會縮小到這裡。你可以隨意拖曳它，或點擊它重新放大！")
                            .outerCircleColor(targetColorRes)
                            .targetCircleColor(android.R.color.white)
                            .titleTextSize(24).descriptionTextSize(16)
                            .textColor(android.R.color.white).transparentTarget(true).drawShadow(true).cancelable(false),
                        object : TapTargetView.Listener() {
                            override fun onTargetClick(view: TapTargetView?) {
                                super.onTargetClick(view)
                                // 點擊只負責拔除定時器，交給 onTargetDismissed 完結
                                autoJumpHandler.removeCallbacks(finishGuideRunnable)
                            }
                            override fun onTargetDismissed(view: TapTargetView?, userInitiated: Boolean) {
                                super.onTargetDismissed(view, userInitiated)
                                sharedPref.edit().putBoolean("IS_FIRST_TIME_HISTORY_DETAIL", false).apply()
                            }
                        }
                    )
                    autoJumpHandler.postDelayed(finishGuideRunnable, 3000)
                }
            }

            // 2️⃣ 第二步：AI 醫生處方箋
            val startStep2 = {
                if (currentStep == 2) { // 確保只執行一次
                    SoundManager.playBubblePop()
                    targetView2 = TapTargetView.showFor(this,
                        TapTarget.forView(tvAdvice, "AI 醫生處方箋", "這裡顯示了歷史病害分析與澆水除蟲建議，幫你隨時複習對症下藥！")
                            .outerCircleColor(targetColorRes)
                            .targetCircleColor(android.R.color.white)
                            .titleTextSize(24).descriptionTextSize(16)
                            .textColor(android.R.color.white).transparentTarget(true).drawShadow(true).cancelable(false),
                        object : TapTargetView.Listener() {
                            override fun onTargetClick(view: TapTargetView?) {
                                super.onTargetClick(view)
                                // 點擊只負責拔除定時器
                                autoJumpHandler.removeCallbacks(jumpToStep3Runnable)
                            }
                            override fun onTargetDismissed(view: TapTargetView?, userInitiated: Boolean) {
                                super.onTargetDismissed(view, userInitiated)
                                // 消失時統一安全推進到第三步
                                if (currentStep == 2) {
                                    currentStep = 3
                                    startStep3()
                                }
                            }
                        }
                    )
                    autoJumpHandler.postDelayed(jumpToStep3Runnable, 3000)
                }
            }

            // 1️⃣ 第一步：雙指縮放看細節
            targetView1 = TapTargetView.showFor(this,
                TapTarget.forView(imgPlant, "點擊放大回顧", "點擊這張過去拍攝的照片，就能進入全螢幕模式！")
                    .outerCircleColor(targetColorRes)
                    .targetCircleColor(android.R.color.white)
                    .titleTextSize(24).descriptionTextSize(16)
                    .textColor(android.R.color.white).transparentTarget(true).drawShadow(true).cancelable(false),
                object : TapTargetView.Listener() {
                    override fun onTargetClick(view: TapTargetView?) {
                        super.onTargetClick(view)
                        // 點擊只負責拔除定時器
                        autoJumpHandler.removeCallbacks(jumpToStep2Runnable)
                    }
                    override fun onTargetDismissed(view: TapTargetView?, userInitiated: Boolean) {
                        super.onTargetDismissed(view, userInitiated)

                        // 無論時間到還是手動點，消失時「唯一執行一次」前進邏輯
                        if (currentStep == 1) {
                            currentStep = 2

                            // 強制手動展開卡片
                            behavior.state = BottomSheetBehavior.STATE_EXPANDED

                            // 延遲 400 毫秒等 BottomSheet 展開動畫跑完，再漂亮地喚醒第二步
                            autoJumpHandler.postDelayed({ startStep2() }, 400)
                        }
                    }
                }
            )
            autoJumpHandler.postDelayed(jumpToStep2Runnable, 3000)
        }
    }

    private fun fetchData() {
        val sharedPref = getSharedPreferences("PlantDoctor", Context.MODE_PRIVATE)
        val token = sharedPref.getString("token", "") ?: ""

        PlantApiService.create(token).getDiaryDetail(diaryId).enqueue(object : Callback<DetailDetailResponse> {
            override fun onResponse(call: Call<DetailDetailResponse>, response: Response<DetailDetailResponse>) {
                if (response.isSuccessful) {
                    val data = response.body()?.data ?: return

                    val tagSuffix = if (!data.plant_tag.isNullOrBlank()) " [${data.plant_tag}]" else ""
                    tvPlantName.text = "植物：${data.crop_name ?: "無法辨識"}$tagSuffix"

                    if (!data.user_corrected_status.isNullOrBlank()) {
                        tvDiseaseName.text = "原診斷：${data.status_name ?: "未知"}\n專家覆核定案：${data.user_corrected_status}"
                    } else {
                        tvDiseaseName.text = "診斷：${data.status_name ?: "未知"}"
                    }
                    tvDiseaseName.setTextColor(tvPlantName.currentTextColor)

                    val fullAdvice = StringBuilder().apply {
                        append("【病症狀態】\n${data.suggestion ?: "尚無建議"}\n\n")
                        append("【治療方法】\n${data.treatment ?: "請諮詢專業人員"}\n\n")
                        append("【過往筆記】")
                    }.toString()
                    tvAdvice.text = fullAdvice

                    // 🌟 核心升級：將處方箋優雅拆解為獨立的卡片區塊
                    tvDetailSymptom.text = data.suggestion ?: "目前植株狀態穩定，無異常嚴重病徵。"
                    tvDetailTreatment.text = data.treatment ?: "請維持良好光照與通風，適度澆水即可。"

                    // 判斷此植株當前是否為健康狀態
                    val isHealthyPlant = (data.user_corrected_status ?: data.status_name ?: "").contains("健康")

                    // 🌟 動態更新病徵卡片環境與安全標籤 (豐富卡片資訊，跨端排版一致)
                    val chipPet = findViewById<TextView?>(R.id.chip_pet_status)
                    val chipEnv = findViewById<TextView?>(R.id.chip_env_status)
                    if (isHealthyPlant) {
                        chipPet?.text = "🐾 環境無風險"
                        chipEnv?.text = "🌱 正常養護環境"
                    } else {
                        val treatStr = data.treatment ?: ""
                        if (treatStr.contains("避開") || treatStr.contains("CAUTION")) {
                            chipPet?.text = "⚠️ 避開毛孩舔拭"
                        } else {
                            chipPet?.text = "🐾 寵物低風險"
                        }
                        chipEnv?.text = "🏠 通風採光處"
                    }

                    // 點擊「官方用藥寶典 ➜」直接攜帶作物與病名快速開啟寶典
                    if (isHealthyPlant) {
                        btnOpenRemedyCatalog.visibility = View.GONE
                        btnCareCheckin.text = "💧 記錄今日已澆水"
                    } else {
                        btnOpenRemedyCatalog.visibility = View.VISIBLE
                        btnCareCheckin.text = "🌿 記錄今日已噴藥"
                        btnOpenRemedyCatalog.setOnClickListener {
                            SoundManager.playBubblePop()
                            val intent = Intent(this@HistoryDetailActivity, RemedyCatalogActivity::class.java).apply {
                                val targetQuery = data.user_corrected_status ?: data.status_name ?: ""
                                if (targetQuery.isNotBlank() && targetQuery != "健康") {
                                    putExtra("EXTRA_SEARCH_QUERY", targetQuery)
                                    putExtra("AUTO_QUERY", targetQuery)
                                }
                            }
                            startActivity(intent)
                        }
                    }

                    // 點擊一鍵照護打卡（健康時打卡澆水，生病時打卡噴藥）
                    btnCareCheckin.setOnClickListener {
                        SoundManager.playBubblePop()
                        handleCareCheckin(isHealthyPlant)
                    }

                    currentImageUrl = fixImageUrl(data.image_url ?: "")

                    Glide.with(this@HistoryDetailActivity).load(currentImageUrl).placeholder(android.R.drawable.ic_menu_gallery).into(imgPlant)
                    Glide.with(this@HistoryDetailActivity).load(currentImageUrl).placeholder(android.R.drawable.ic_menu_gallery).into(imgPipPlant)

                    tvUserNoteDisplay.text = data.user_note ?: "點選右側鉛筆圖示新增筆記"
                    switchToDisplayMode()

                    setupHistoryDetailGuide()
                    // 🌟 同步載入本株植物專屬的康復時間軸與 Before/After 比對
                    fetchTimelineData()
                }
            }
            override fun onFailure(call: Call<DetailDetailResponse>, t: Throwable) {
                Toast.makeText(this@HistoryDetailActivity, "載入失敗", Toast.LENGTH_SHORT).show()
            }
        })
    }

    private fun fetchTimelineData() {
        val sharedPref = getSharedPreferences("PlantDoctor", Context.MODE_PRIVATE)
        val token = sharedPref.getString("token", "") ?: ""

        PlantApiService.create(token).getDiaryTimeline(diaryId).enqueue(object : Callback<TimelineResponse> {
            override fun onResponse(call: Call<TimelineResponse>, response: Response<TimelineResponse>) {
                if (response.isSuccessful && response.body() != null) {
                    val body = response.body()!!
                    renderTimeline(body)
                }
            }

            override fun onFailure(call: Call<TimelineResponse>, t: Throwable) {
                // 靜默降級，不影響原本處方箋的閱覽
            }
        })
    }

    private fun renderTimeline(data: TimelineResponse) {
        if (!data.plantTag.isNullOrBlank()) {
            tvTimelineHeaderTitle.text = "🌱 【${data.plantTag}】專屬康復時間軸與生長監控"
        } else {
            tvTimelineHeaderTitle.text = "🌱 單株專屬康復時間軸與生長監控"
        }
        tvTrendTitle.text = data.trendTitle
        tvTrendDesc.text = data.trendDesc

        // 依趨勢顏色高亮卡片標題
        when (data.trendStatus) {
            "RECOVERED" -> tvTrendTitle.setTextColor(Color.parseColor("#2E7D32"))
            "ALERT" -> tvTrendTitle.setTextColor(Color.parseColor("#C62828"))
            "TRANSITION", "TREATING" -> tvTrendTitle.setTextColor(Color.parseColor("#E65100"))
            else -> tvTrendTitle.setTextColor(Color.parseColor("#1B5E20"))
        }

        // 處理 Before vs After 對比
        if (data.hasBeforeAfter && data.beforeRecord != null && data.afterRecord != null) {
            layoutBeforeAfter.visibility = View.VISIBLE

            // 🌟 動態切換標題：健康轉健康叫「成長發育寫真」，生病轉健康才叫「康復成效對照」
            tvCompareTitle.text = data.compareTitle ?: "🔍 歷程影像對比 (Before vs After)"

            val before = data.beforeRecord
            val after = data.afterRecord

            tvBeforeLabel.text = data.beforeLabel ?: (if (before.isHealthy) "初期：健康" else "初期：${before.statusName}")
            tvBeforeDate.text = before.createdAt.take(10)
            val beforeUrl = fixImageUrl(before.imageUrl)
            Glide.with(this).load(beforeUrl).placeholder(android.R.drawable.ic_menu_gallery).into(imgBefore)
            cvBeforeImg.setOnClickListener {
                SoundManager.playBubblePop()
                startActivity(Intent(this, ImagePreviewActivity::class.java).apply {
                    putExtra("IMAGE_PATH", beforeUrl)
                })
            }

            tvAfterLabel.text = data.afterLabel ?: (if (after.isHealthy) "現況：健康" else "現況：${after.statusName}")
            tvAfterDate.text = after.createdAt.take(10)
            val afterUrl = fixImageUrl(after.imageUrl)
            Glide.with(this).load(afterUrl).placeholder(android.R.drawable.ic_menu_gallery).into(imgAfter)
            cvAfterImg.setOnClickListener {
                SoundManager.playBubblePop()
                startActivity(Intent(this, ImagePreviewActivity::class.java).apply {
                    putExtra("IMAGE_PATH", afterUrl)
                })
            }
        } else {
            layoutBeforeAfter.visibility = View.GONE
        }

        // 渲染垂直節點列表
        containerTimelineNodes.removeAllViews()
        val inflater = layoutInflater

        data.timeline.forEachIndexed { index, node ->
            val nodeView = inflater.inflate(R.layout.item_timeline_node, containerTimelineNodes, false)

            val viewDot = nodeView.findViewById<View>(R.id.view_dot)
            val viewLine = nodeView.findViewById<View>(R.id.view_line)
            val imgThumb = nodeView.findViewById<ImageView>(R.id.img_node_thumb)
            val tvStatus = nodeView.findViewById<TextView>(R.id.tv_node_status)
            val tvTag = nodeView.findViewById<TextView>(R.id.tv_node_tag)
            val tvDate = nodeView.findViewById<TextView>(R.id.tv_node_date)
            val tvNote = nodeView.findViewById<TextView>(R.id.tv_node_note)
            val cardNode = nodeView.findViewById<CardView>(R.id.card_timeline_node)

            // 如果是最後一個節點，隱藏連接下方的線條
            if (index == data.timeline.size - 1) {
                viewLine.visibility = View.INVISIBLE
            }

            // 狀態與樣式
            if (node.isHealthy) {
                tvStatus.text = "🌿 健康狀態"
                tvStatus.setTextColor(Color.parseColor("#2E7D32"))
                viewDot.backgroundTintList = getColorStateList(android.R.color.holo_green_dark)
            } else {
                tvStatus.text = "🦠 ${node.statusName}"
                tvStatus.setTextColor(Color.parseColor("#C62828"))
                viewDot.backgroundTintList = getColorStateList(android.R.color.holo_red_light)
            }

            tvDate.text = node.createdAt

            // 當前檢視標籤
            if (node.isCurrent) {
                tvTag.visibility = View.VISIBLE
                cardNode.setCardBackgroundColor(Color.parseColor("#E8F5E9"))
            } else {
                tvTag.visibility = View.GONE
                cardNode.setCardBackgroundColor(Color.parseColor("#FFFFFF"))
            }

            // 筆記
            if (node.userNote.isNotBlank()) {
                tvNote.visibility = View.VISIBLE
                tvNote.text = "📝 ${node.userNote}"
            } else {
                tvNote.visibility = View.GONE
            }

            // 縮圖
            val nodeImgUrl = fixImageUrl(node.imageUrl)
            Glide.with(this).load(nodeImgUrl).placeholder(android.R.drawable.ic_menu_gallery).into(imgThumb)

            // 點擊節點卡片切換至該病例（若不是當前頁）
            cardNode.setOnClickListener {
                if (node.id != diaryId) {
                    SoundManager.playBubblePop()
                    val intent = Intent(this, HistoryDetailActivity::class.java).apply {
                        putExtra("DIARY_ID", node.id)
                    }
                    startActivity(intent)
                    finish()
                }
            }

            containerTimelineNodes.addView(nodeView)
        }
    }

    private fun fixImageUrl(rawUrl: String): String {
        // 1. 安全防禦：如果是測試環境儲存的本地 Uri 路徑，直接回傳
        if (rawUrl.startsWith("content://") || rawUrl.startsWith("file://")) {
            return rawUrl
        }

        // 2. 🌟 核心進化：直接跟 API 拿目前已經探路成功的正確主機或 IP
        val resolvedIp = com.example.plantdoctor.PlantApiService.currentRunningIp
        val isCloud = resolvedIp.contains("railway.app")
        val schemeAndHost = when {
            isCloud -> "https://$resolvedIp"
            resolvedIp.startsWith("http://") || resolvedIp.startsWith("https://") -> resolvedIp.trimEnd('/')
            else -> "http://$resolvedIp:8000"
        }

        // 3. 把後端傳來的 127.0.0.1 或 localhost 置換為正確主機
        var url = rawUrl
            .replace("http://127.0.0.1:8000", schemeAndHost)
            .replace("http://localhost:8000", schemeAndHost)
            .replace("127.0.0.1", resolvedIp)
            .replace("localhost", resolvedIp)

        // 4. 基本相對路徑防禦
        if (!url.startsWith("http://") && !url.startsWith("https://")) {
            val safePath = if (url.startsWith("/")) url else "/$url"
            url = "$schemeAndHost$safePath"
        }

        // 5. static/ 路由防禦
        val keywordStatic = "static/"
        if (url.contains(keywordStatic)) {
            val startIndex = url.indexOf(keywordStatic)
            url = "$schemeAndHost/$keywordStatic" + url.substring(startIndex + keywordStatic.length)
        }

        // 6. uploads/ 路由防禦
        val keywordUploads = "uploads/"
        if (url.contains(keywordUploads)) {
            val startIndex = url.indexOf(keywordUploads)
            url = "$schemeAndHost/$keywordUploads" + url.substring(startIndex + keywordUploads.length)
        }

        android.util.Log.d("FixImageUrl", "🖼️ 圖片網址最終修復為: $url")
        return url
    }

    private fun executeDelete() {
        val sharedPref = getSharedPreferences("PlantDoctor", Context.MODE_PRIVATE)
        val token = sharedPref.getString("token", "") ?: ""

        PlantApiService.create(token).deleteDiary(diaryId).enqueue(object : Callback<GenericResponse> {
            override fun onResponse(call: Call<GenericResponse>, response: Response<GenericResponse>) {
                if (response.isSuccessful) {
                    Toast.makeText(this@HistoryDetailActivity, "刪除成功", Toast.LENGTH_SHORT).show()
                    setResult(RESULT_OK)
                    finish()
                } else {
                    Toast.makeText(this@HistoryDetailActivity, "刪除失敗: ${response.code()}", Toast.LENGTH_SHORT).show()
                }
            }
            override fun onFailure(call: Call<GenericResponse>, t: Throwable) {
                Toast.makeText(this@HistoryDetailActivity, "刪除失敗: 網路連線問題", Toast.LENGTH_SHORT).show()
            }
        })
    }

    override fun onTouchEvent(event: MotionEvent?): Boolean {
        if (event != null) {
            when (event.action) {
                MotionEvent.ACTION_DOWN -> windHandler.postDelayed(windRunnable, 500)
                MotionEvent.ACTION_UP, MotionEvent.ACTION_CANCEL -> {
                    windHandler.removeCallbacks(windRunnable)
                    SoundManager.stopWind()
                }
            }
        }
        return super.onTouchEvent(event)
    }

    override fun onStop() {
        super.onStop()
        SoundManager.stopWind()
        windHandler.removeCallbacks(windRunnable)
    }

    override fun onDestroy() {
        super.onDestroy()
        windHandler.removeCallbacksAndMessages(null)
    }



    // 🌟 全新新增：刪除確認對話框（直接套用儲存確認的樣式與 ThemeManager 變色機制）
    private fun showDeleteConfirmationDialog() {
        // 1. 直接複用之前刻好的自訂佈局
        val dialogView = layoutInflater.inflate(R.layout.dialog_save_confirm, null)

        val builder = AlertDialog.Builder(this)
        builder.setView(dialogView)
        builder.setCancelable(true)

        val alertDialog = builder.create()
        alertDialog.window?.setBackgroundDrawableResource(android.R.color.transparent)
        alertDialog.show()
        val dialogWidth = (resources.displayMetrics.widthPixels * 0.90).toInt()
        alertDialog.window?.setLayout(dialogWidth, android.view.ViewGroup.LayoutParams.WRAP_CONTENT)

        // 2. 綁定自訂對話框的畫面元件
        val cardRoot = dialogView.findViewById<CardView>(R.id.dialog_card_root)
        val btnClose = dialogView.findViewById<ImageButton>(R.id.dialog_btn_close)
        val tvTitle = dialogView.findViewById<TextView>(R.id.dialog_title)
        val tvMessage = dialogView.findViewById<TextView>(R.id.dialog_message)
        val btnConfirmDelete = dialogView.findViewById<Button>(R.id.dialog_btn_save) // 複用儲存按鈕位置當確認鍵
        val btnCancel = dialogView.findViewById<Button>(R.id.dialog_btn_dont_save)     // 複用不儲存按鈕位置當取消鍵

        // 🌟 3. 動態更換文字：將原本的「儲存提示」替換成「刪除提示」
        tvTitle.text = "確認刪除病例"
        tvMessage.text = "刪除後將無法恢復此筆紀錄，\n您確定要刪除這筆歷史病例嗎？"

        // 更換按鈕文字與色彩語意
        btnConfirmDelete.text = "確定刪除"
        btnConfirmDelete.backgroundTintList = getColorStateList(android.R.color.holo_red_dark) // 🌟 刪除是危險動作，將主按鈕改成深紅色

        btnCancel.text = "取消"
        btnCancel.backgroundTintList = getColorStateList(android.R.color.darker_gray)         // 取消改成灰色

        // 🌟 4. 風格染色：直接呼叫先前在 ThemeManager 擴充的方法，讓背景與文字顏色完全跟隨 KT 風格
        ThemeManager.applyThemeToDialog(
            context = this,
            cardRoot = cardRoot,
            btnClose = btnClose,
            tvTitle = tvTitle,
            tvMessage = tvMessage
        )

        // 5. 綁定按鈕監聽事件
        // 左上角叉叉 ＝ 關掉對話框
        btnClose.setOnClickListener {
            SoundManager.playBubblePop()
            alertDialog.dismiss()
        }

        // 綠色按鈕位置（已被我們改為確定刪除）
        btnConfirmDelete.setOnClickListener {
            alertDialog.dismiss()
            executeDelete() // 真正執行刪除 API
        }

        // 紅色按鈕位置（已被我們改為取消）
        btnCancel.setOnClickListener {
            SoundManager.playBubblePop()
            alertDialog.dismiss() // 單純關閉對話框，留在原頁
        }
    }

}
