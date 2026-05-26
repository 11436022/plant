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
    private lateinit var tvFeedbackLink: TextView
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
        setupHistoryDetailGuide()
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
        tvFeedbackLink = findViewById(R.id.tv_feedback_link)

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

        btnAction.setOnClickListener {
            SoundManager.playBubblePop()
            executeDelete()
        }

        btnBack.setOnClickListener {
            SoundManager.playBubblePop()
            finish()
        }

        imgPlant.setOnClickListener { openImagePreview() }
        cvPipContainer.setOnClickListener { openImagePreview() }

        tvFeedbackLink.setOnClickListener {
            SoundManager.playBubblePop()
            showDiagnosesSelectionDialog()
        }

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

            val jumpToStep2Runnable = Runnable { targetView1?.dismiss(true) }
            val jumpToStep3Runnable = Runnable { targetView2?.dismiss(true) }
            val finishGuideRunnable = Runnable { targetView3?.dismiss(true) }

            // 3️⃣ 第三步：懸浮窗小圖
            val startStep3 = {
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
                            autoJumpHandler.removeCallbacks(finishGuideRunnable)
                            sharedPref.edit().putBoolean("IS_FIRST_TIME_HISTORY_DETAIL", false).apply()
                        }
                        override fun onTargetDismissed(view: TapTargetView?, userInitiated: Boolean) {
                            super.onTargetDismissed(view, userInitiated)
                            sharedPref.edit().putBoolean("IS_FIRST_TIME_HISTORY_DETAIL", false).apply()
                        }
                    }
                )
                autoJumpHandler.postDelayed(finishGuideRunnable, 3000)
            }

            // 2️⃣ 第二步：AI 醫生處方箋（展開後才介紹）
            val startStep2 = {
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
                            autoJumpHandler.removeCallbacks(jumpToStep3Runnable)
                            startStep3()
                        }
                        override fun onTargetDismissed(view: TapTargetView?, userInitiated: Boolean) {
                            super.onTargetDismissed(view, userInitiated)
                            startStep3()
                        }
                    }
                )
                autoJumpHandler.postDelayed(jumpToStep3Runnable, 3000)
            }

            // 🌟 將剛剛寫在監聽器上方的 startStep2 指向實作，讓 BottomSheet 展開後可以呼叫
            // （如果你是在 initViews 裡宣告，可以直接將此處的 startStep2 賦值給全域/區域變數）
            // 這裡為了邏輯連貫，也可以直接利用剛才設定在行為裡的 Callback

            // 1️⃣ 第一步：雙指縮放看細節
            targetView1 = TapTargetView.showFor(this,
                TapTarget.forView(imgPlant, "點擊放大回顧", "點擊這張過去拍攝的照片，就能進入全螢幕模式！")
                    .outerCircleColor(targetColorRes)
                    .targetCircleColor(android.R.color.white)
                    .titleTextSize(24).descriptionTextSize(16)
                    .textColor(android.R.color.white).transparentTarget(true).drawShadow(true).cancelable(false),
                object : TapTargetView.Listener() {
                    private fun proceedToExpand() {
                        autoJumpHandler.removeCallbacks(jumpToStep2Runnable)
                        // 🌟 強制手動展開卡片，展開成功後透過 Callback 就會觸發 startStep2 囉！
                        behavior.state = BottomSheetBehavior.STATE_EXPANDED

                        // 防禦防漏：若監聽器沒串好，可以直接在 300 毫秒後強制補刀啟動第二步
                        autoJumpHandler.postDelayed({ startStep2() }, 400)
                    }
                    override fun onTargetClick(view: TapTargetView?) {
                        super.onTargetClick(view)
                        proceedToExpand()
                    }
                    override fun onTargetDismissed(view: TapTargetView?, userInitiated: Boolean) {
                        super.onTargetDismissed(view, userInitiated)
                        proceedToExpand()
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

                    tvPlantName.text = "植物：${data.crop_name ?: "無法辨識"}"

                    if (!data.user_corrected_status.isNullOrEmpty()) {
                        tvDiseaseName.text = "診斷：${data.user_corrected_status}"
                        tvDiseaseName.setTextColor(Color.parseColor("#2E7D32"))
                        tvFeedbackLink.visibility = View.GONE
                    } else {
                        tvDiseaseName.text = "診斷：${data.status_name ?: "未知"}"
                        tvDiseaseName.setTextColor(Color.RED)
                        tvFeedbackLink.visibility = View.VISIBLE
                    }

                    val fullAdvice = "【專家建議】\n${data.suggestion ?: "尚無建議"}\n\n【治療方法】\n${data.treatment ?: "請諮詢專業人員"}"
                    tvAdvice.text = fullAdvice
                    currentImageUrl = fixImageUrl(data.image_url ?: "")

                    Glide.with(this@HistoryDetailActivity).load(currentImageUrl).placeholder(android.R.drawable.ic_menu_gallery).into(imgPlant)
                    Glide.with(this@HistoryDetailActivity).load(currentImageUrl).placeholder(android.R.drawable.ic_menu_gallery).into(imgPipPlant)

                    tvUserNoteDisplay.text = data.user_note ?: "點選右側鉛筆圖示新增筆記"
                    switchToDisplayMode()
                }
            }
            override fun onFailure(call: Call<DetailDetailResponse>, t: Throwable) {
                Toast.makeText(this@HistoryDetailActivity, "載入失敗", Toast.LENGTH_SHORT).show()
            }
        })
    }

    private fun fixImageUrl(rawUrl: String): String {
        // 🌟 新增防禦：如果是測試環境儲存的本地 Uri 路徑，直接回傳，不要去破壞它！
        if (rawUrl.startsWith("content://") || rawUrl.startsWith("file://")) {
            return rawUrl
        }

        var url = rawUrl.replace("127.0.0.1", "10.0.2.2").replace("localhost", "10.0.2.2")
        val keyword = "static/"
        if (url.contains(keyword)) {
            val startIndex = url.indexOf(keyword)
            val firstSlash = url.indexOf("/", 8)
            if (firstSlash != -1) {
                val baseUrl = url.substring(0, firstSlash + 1)
                return baseUrl + url.substring(startIndex)
            }
        }
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

    private fun showDiagnosesSelectionDialog() {
        val loadingDialog = AlertDialog.Builder(this).setView(R.layout.dialog_loading).setCancelable(false).create()
        loadingDialog.show()

        val sharedPref = getSharedPreferences("PlantDoctor", Context.MODE_PRIVATE)
        val token = sharedPref.getString("token", "") ?: ""

        PlantApiService.create(token).getDiagnoses().enqueue(object : Callback<DiagnosesResponse> {
            override fun onResponse(call: Call<DiagnosesResponse>, response: Response<DiagnosesResponse>) {
                loadingDialog.dismiss()
                if (response.isSuccessful) {
                    val diagnoses = response.body()?.data ?: emptyList()
                    if (diagnoses.isEmpty()) return
                    val items = diagnoses.map { it.name }.toTypedArray()

                    AlertDialog.Builder(this@HistoryDetailActivity)
                        .setTitle("回報診斷結果")
                        .setItems(items) { dialog, which ->
                            val selectedDiagnosis = items[which]
                            val request = PatchDiaryRequest(user_corrected_status = selectedDiagnosis)

                            PlantApiService.create(token).patchDiary(diaryId, request).enqueue(object : Callback<GenericResponse> {
                                override fun onResponse(call: Call<GenericResponse>, response: Response<GenericResponse>) {
                                    if (response.isSuccessful) {
                                        Toast.makeText(this@HistoryDetailActivity, "回饋已提交！", Toast.LENGTH_LONG).show()
                                        tvDiseaseName.text = "診斷：$selectedDiagnosis"
                                        tvDiseaseName.setTextColor(Color.parseColor("#2E7D32"))
                                        tvFeedbackLink.visibility = View.GONE
                                    }
                                }
                                override fun onFailure(call: Call<GenericResponse>, t: Throwable) {}
                            })
                        }.setNegativeButton("取消", null).show()
                }
            }
            override fun onFailure(call: Call<DiagnosesResponse>, t: Throwable) { loadingDialog.dismiss() }
        })
    }
}