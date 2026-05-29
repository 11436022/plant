package com.example.plantdoctor

import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.util.Log
import android.view.MotionEvent
import android.view.View
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
import androidx.room.util.copy
import com.bumptech.glide.Glide
import com.google.android.material.bottomsheet.BottomSheetBehavior
import com.google.gson.Gson

class ResultActivity : AppCompatActivity() {

    private val windHandler = Handler(Looper.getMainLooper())
    private val windRunnable = Runnable {
        SoundManager.startWind()
    }

    private lateinit var resultRoot: CoordinatorLayout
    private lateinit var btnBack: ImageButton
    private lateinit var btnSave: Button
    private lateinit var tvMainTitle: TextView
    private lateinit var cvImageContainer: CardView
    private lateinit var cvPipContainer: CardView
    private lateinit var imgPipPlant: ImageView
    private lateinit var cardAdvice: CardView
    private lateinit var etUserNote: EditText
    private lateinit var tvDiseaseName: TextView
    private lateinit var tvAdvice: TextView

    private var dX = 0f
    private var dY = 0f
    private var startX = 0f
    private var startY = 0f
    private var isDragging = false

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_result)

        val sharedPref = getSharedPreferences("PlantDoctor", MODE_PRIVATE)

        // 1. 綁定元件
        resultRoot = findViewById(R.id.result_root_layout)
        btnBack = findViewById(R.id.btn_back_home)
        btnSave = findViewById(R.id.btn_save_report)
        val tvPlantName = findViewById<TextView>(R.id.tv_plant_name)
        tvDiseaseName = findViewById(R.id.tv_disease_name)
        tvAdvice = findViewById(R.id.tv_advice)
        val imgPlant = findViewById<ImageView>(R.id.img_result_plant)
        tvMainTitle = findViewById(R.id.tv_title)
        cvImageContainer = findViewById(R.id.cv_image_container)
        cardAdvice = findViewById(R.id.card_advice)
        etUserNote = findViewById(R.id.et_user_note)

        val viewDragHandle = findViewById<View>(R.id.view_drag_handle)
        cvPipContainer = findViewById(R.id.cv_pip_container)
        imgPipPlant = findViewById(R.id.img_pip_plant)

        // 2. BottomSheet 監聽與最高高度限制
        val behavior = BottomSheetBehavior.from(cardAdvice)

        tvMainTitle.post {
            val titleBottom = tvMainTitle.bottom
            val marginPx = (10 * resources.displayMetrics.density).toInt()
            behavior.expandedOffset = titleBottom + marginPx
        }

        // 3. 新手指引狀態變數
        val isFirstTimeResult = sharedPref.getBoolean("IS_FIRST_TIME_RESULT", true)
        var startStep3: (() -> Unit)? = null

        behavior.addBottomSheetCallback(object : BottomSheetBehavior.BottomSheetCallback() {
            override fun onStateChanged(bottomSheet: View, newState: Int) {
                if (newState == BottomSheetBehavior.STATE_EXPANDED) {
                    cvPipContainer.visibility = View.VISIBLE
                    cvPipContainer.alpha = 1f

                    if (isFirstTimeResult) {
                        startStep3?.invoke()
                        startStep3 = null
                    }
                } else if (newState == BottomSheetBehavior.STATE_COLLAPSED) {
                    cvPipContainer.visibility = View.GONE
                }
            }

            override fun onSlide(bottomSheet: View, slideOffset: Float) {
                tvMainTitle.alpha = 1f
                cvImageContainer.alpha = 1f

                if (slideOffset > 0.8f) {
                    //  修正為下面這一行：正常指定為 View.VISIBLE 即可！
                    cvPipContainer.visibility = View.VISIBLE
                    cvPipContainer.alpha = (slideOffset - 0.8f) * 5f
                } else {
                    cvPipContainer.visibility = View.GONE
                }
            }
        })

        // 4. 接收資料並載入
        val imageUriString = intent.getStringExtra("IMAGE_URI")
        val predictionId = intent.getStringExtra("PREDICTION_ID")
        val resultJson = intent.getStringExtra("ANALYSIS_RESULT_JSON")

        if (!imageUriString.isNullOrEmpty()) {
            val uri = Uri.parse(imageUriString)
            Glide.with(this).load(uri).into(imgPlant)
            Glide.with(this).load(uri).into(imgPipPlant)
        }

        imgPlant.setOnClickListener {
            if (!imageUriString.isNullOrEmpty()) {
                SoundManager.playBubblePop()
                val intent = Intent(this, ImagePreviewActivity::class.java).apply {
                    putExtra("IMAGE_PATH", imageUriString)
                }
                startActivity(intent)
            }
        }

        setupPipDragListener(imageUriString)

        if (predictionId.isNullOrEmpty() || resultJson.isNullOrEmpty()) {
            Toast.makeText(this, "無法載入分析結果", Toast.LENGTH_SHORT).show()
            finish()
            return
        }

        try {
            val data = Gson().fromJson(resultJson, AnalysisResult::class.java)
            tvPlantName.text = "植物：${data.crop_name ?: "無法辨識"}"
            tvDiseaseName.text = "診斷：${data.status_name ?: "未知"}"

            val fullAdvice = StringBuilder().apply {
                append("【專家建議】\n${data.suggestion ?: "尚無建議"}\n\n")
                //append("【治療方法】\n${data.treatment ?: "請諮詢專業人員"}")
            }.toString()
            tvAdvice.text = fullAdvice
        } catch (e: Exception) {
            e.printStackTrace()
            Toast.makeText(this, "報告內容解析失敗", Toast.LENGTH_SHORT).show()
        }

        // 🌟 修改後：點擊左上角返回鍵，跳出未儲存提示對話框
        btnBack.setOnClickListener {
            SoundManager.playBubblePop()
            showSaveConfirmationDialog(predictionId)
        }

        // 🌟 還原後：點擊右下角儲存，直接執行儲存
        btnSave.setOnClickListener {
            SoundManager.playBubblePop()
            val sharedPref = getSharedPreferences("PlantDoctor", MODE_PRIVATE)
            executeSaveLogic(predictionId, sharedPref)
        }

        // 🌟 啟動防連點、防重複指引邏輯
        if (isFirstTimeResult) {
            val targetColorRes = android.R.color.holo_green_dark
            val guideHandler = Handler(Looper.getMainLooper())

            var targetView1: com.getkeepsafe.taptargetview.TapTargetView? = null
            var targetView2: com.getkeepsafe.taptargetview.TapTargetView? = null
            var targetView3: com.getkeepsafe.taptargetview.TapTargetView? = null
            var targetView4: com.getkeepsafe.taptargetview.TapTargetView? = null
            var targetView5: com.getkeepsafe.taptargetview.TapTargetView? = null

            // 狀態鎖控制
            var currentStep = 1

            val jumpToStep2Runnable = Runnable { targetView1?.dismiss(true) }
            val jumpToStep3Runnable = Runnable { targetView2?.dismiss(true) }
            val jumpToStep4Runnable = Runnable { targetView3?.dismiss(true) }
            val jumpToStep5Runnable = Runnable { targetView4?.dismiss(true) }
            val finishGuideRunnable = Runnable { targetView5?.dismiss(true) }

            // 5️⃣ 第五步：儲存按鈕
            val startStep5 = {
                if (currentStep == 5) {
                    SoundManager.playBubblePop()
                    targetView5 = com.getkeepsafe.taptargetview.TapTargetView.showFor(this,
                        com.getkeepsafe.taptargetview.TapTarget.forView(
                            btnSave, "第五步：儲存至歷史病例", "最後，點擊這裡可以把這次的診斷結果與你的觀察筆記永久保存下來！"
                        ).outerCircleColor(targetColorRes)
                            .targetCircleColor(android.R.color.white)
                            .titleTextSize(24).descriptionTextSize(16)
                            .textColor(android.R.color.white).transparentTarget(true).drawShadow(true).cancelable(false),
                        object : com.getkeepsafe.taptargetview.TapTargetView.Listener() {
                            override fun onTargetClick(view: com.getkeepsafe.taptargetview.TapTargetView?) {
                                super.onTargetClick(view)
                                guideHandler.removeCallbacks(finishGuideRunnable)
                            }
                            override fun onTargetDismissed(view: com.getkeepsafe.taptargetview.TapTargetView?, userInitiated: Boolean) {
                                super.onTargetDismissed(view, userInitiated)
                                sharedPref.edit().putBoolean("IS_FIRST_TIME_RESULT", false).apply()
                            }
                        }
                    )
                    guideHandler.postDelayed(finishGuideRunnable, 3000)
                }
            }

            // 4️⃣ 第四步：浮動縮小小圖
            val startStep4 = {
                if (currentStep == 4) {
                    SoundManager.playBubblePop()
                    targetView4 = com.getkeepsafe.taptargetview.TapTargetView.showFor(this,
                        com.getkeepsafe.taptargetview.TapTarget.forView(
                            cvPipContainer, "第四步：小窗隨身看", "展開報告後，照片會縮小到這裡。你可以隨意拖曳它，或點擊它重新放大！"
                        ).outerCircleColor(targetColorRes)
                            .targetCircleColor(android.R.color.white)
                            .titleTextSize(24).descriptionTextSize(16)
                            .textColor(android.R.color.white).transparentTarget(true).drawShadow(true).cancelable(false),
                        object : com.getkeepsafe.taptargetview.TapTargetView.Listener() {
                            override fun onTargetClick(view: com.getkeepsafe.taptargetview.TapTargetView?) {
                                super.onTargetClick(view)
                                guideHandler.removeCallbacks(jumpToStep5Runnable)
                            }
                            override fun onTargetDismissed(view: com.getkeepsafe.taptargetview.TapTargetView?, userInitiated: Boolean) {
                                super.onTargetDismissed(view, userInitiated)
                                if (currentStep == 4) {
                                    currentStep = 5
                                    startStep5()
                                }
                            }
                        }
                    )
                    guideHandler.postDelayed(jumpToStep5Runnable, 3000)
                }
            }

            // 3️⃣ 第三步：AI 醫生處方箋說明
            startStep3 = {
                if (currentStep == 3) {
                    SoundManager.playBubblePop()
                    targetView3 = com.getkeepsafe.taptargetview.TapTargetView.showFor(this,
                        com.getkeepsafe.taptargetview.TapTarget.forView(
                            tvAdvice, "第三步：AI 醫生處方箋", "這裡會顯示詳細的病害分析、澆水與除蟲建議，幫你對症下藥！"
                        ).outerCircleColor(targetColorRes)
                            .targetCircleColor(android.R.color.white)
                            .titleTextSize(24).descriptionTextSize(16)
                            .textColor(android.R.color.white).transparentTarget(true).drawShadow(true).cancelable(false),
                        object : com.getkeepsafe.taptargetview.TapTargetView.Listener() {
                            override fun onTargetClick(view: com.getkeepsafe.taptargetview.TapTargetView?) {
                                super.onTargetClick(view)
                                guideHandler.removeCallbacks(jumpToStep4Runnable)
                            }
                            override fun onTargetDismissed(view: com.getkeepsafe.taptargetview.TapTargetView?, userInitiated: Boolean) {
                                super.onTargetDismissed(view, userInitiated)
                                if (currentStep == 3) {
                                    currentStep = 4
                                    startStep4()
                                }
                            }
                        }
                    )
                    guideHandler.postDelayed(jumpToStep4Runnable, 3000)
                }
            }

            // 2️⃣ 第二步：說明能展開詳細報告
            val startStep2 = {
                if (currentStep == 2) {
                    SoundManager.playBubblePop()
                    targetView2 = com.getkeepsafe.taptargetview.TapTargetView.showFor(this,
                        com.getkeepsafe.taptargetview.TapTarget.forView(
                            viewDragHandle, "第二步：展開完整報告", "將這個卡片向上滑動，就能解鎖 AI 醫生為你準備的完整病害處方箋喔！"
                        ).outerCircleColor(targetColorRes)
                            .targetCircleColor(android.R.color.white)
                            .titleTextSize(24).descriptionTextSize(16)
                            .textColor(android.R.color.white).transparentTarget(true).drawShadow(true).cancelable(false),
                        object : com.getkeepsafe.taptargetview.TapTargetView.Listener() {
                            override fun onTargetClick(view: com.getkeepsafe.taptargetview.TapTargetView?) {
                                super.onTargetClick(view)
                                guideHandler.removeCallbacks(jumpToStep3Runnable)
                            }
                            override fun onTargetDismissed(view: com.getkeepsafe.taptargetview.TapTargetView?, userInitiated: Boolean) {
                                super.onTargetDismissed(view, userInitiated)
                                if (currentStep == 2) {
                                    currentStep = 3
                                    behavior.state = BottomSheetBehavior.STATE_EXPANDED
                                }
                            }
                        }
                    )
                    guideHandler.postDelayed(jumpToStep3Runnable, 3000)
                }
            }

            // 1️⃣ 第一步：雙指縮放看細節
            targetView1 = com.getkeepsafe.taptargetview.TapTargetView.showFor(this,
                com.getkeepsafe.taptargetview.TapTarget.forView(
                    imgPlant, "第一步：雙指縮放看細節", "你可以用兩隻手指放大或縮小這張病害照片，仔細觀察植物微觀病徵！"
                ).outerCircleColor(targetColorRes)
                    .targetCircleColor(android.R.color.white)
                    .titleTextSize(24).descriptionTextSize(16)
                    .textColor(android.R.color.white).transparentTarget(true).drawShadow(true).cancelable(false),
                object : com.getkeepsafe.taptargetview.TapTargetView.Listener() {
                    override fun onTargetClick(view: com.getkeepsafe.taptargetview.TapTargetView?) {
                        super.onTargetClick(view)
                        guideHandler.removeCallbacks(jumpToStep2Runnable)
                    }
                    override fun onTargetDismissed(view: com.getkeepsafe.taptargetview.TapTargetView?, userInitiated: Boolean) {
                        super.onTargetDismissed(view, userInitiated)
                        if (currentStep == 1) {
                            currentStep = 2
                            startStep2()
                        }
                    }
                }
            )
            guideHandler.postDelayed(jumpToStep2Runnable, 3000)
        }
    }

    // 🌟 核心新增：彈出式對話框，具備三個功能按鈕且顏色自適應
    // 🌟 全新客製化對話框：具備左上角叉叉、固定顏色（不隨深色模式改變）
    private fun showSaveConfirmationDialog(predictionId: String?) {
        val sharedPref = getSharedPreferences("PlantDoctor", MODE_PRIVATE)
        val dialogView = layoutInflater.inflate(R.layout.dialog_save_confirm, null)

        val builder = AlertDialog.Builder(this)
        builder.setView(dialogView)
        builder.setCancelable(true)

        val alertDialog = builder.create()
        alertDialog.window?.setBackgroundDrawableResource(android.R.color.transparent)
        alertDialog.show()

        // 1. 綁定元件
        val cardRoot = dialogView.findViewById<CardView>(R.id.dialog_card_root)
        val btnClose = dialogView.findViewById<ImageButton>(R.id.dialog_btn_close)
        val tvTitle = dialogView.findViewById<TextView>(R.id.dialog_title)
        val tvMessage = dialogView.findViewById<TextView>(R.id.dialog_message)
        val btnSaveReport = dialogView.findViewById<Button>(R.id.dialog_btn_save)
        val btnDontSave = dialogView.findViewById<Button>(R.id.dialog_btn_dont_save)

        // 🌟 2. 核心改動：直接呼叫專屬 Dialog 換色器，讓小視窗完美融入當前的 KT 風格！
        ThemeManager.applyThemeToDialog(
            context = this,
            cardRoot = cardRoot,
            btnClose = btnClose,
            tvTitle = tvTitle,
            tvMessage = tvMessage
        )

        // 3. 按鈕點擊監聽
        btnClose.setOnClickListener {
            SoundManager.playBubblePop()
            alertDialog.dismiss()
        }

        btnSaveReport.setOnClickListener {
            alertDialog.dismiss()
            executeSaveLogic(predictionId, sharedPref)
        }

        btnDontSave.setOnClickListener {
            alertDialog.dismiss()
            SoundManager.playBubblePop()
            Toast.makeText(this, "已取消儲存", Toast.LENGTH_SHORT).show()

            val intent = Intent(this, HomeActivity::class.java)
            intent.addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP or Intent.FLAG_ACTIVITY_NEW_TASK)
            startActivity(intent)
            finish()
        }
    }

    // 🌟 將原本的網路儲存邏輯抽離出來供 Dialog 呼叫
    private fun executeSaveLogic(predictionId: String?, sharedPref: android.content.SharedPreferences) {
        val diseaseName = tvDiseaseName.text.toString().removePrefix("診斷：")
        val adviceText = tvAdvice.text.toString()
        val userNote = etUserNote.text.toString()

        val token = sharedPref.getString("token", null)
        if (token == null) {
            Toast.makeText(this, "請先登入", Toast.LENGTH_SHORT).show()
            return
        }

        btnSave.isEnabled = false
        btnSave.text = "儲存中..."

        val request = DiaryConfirmRequest(
            user_note = userNote,
            disease_name = diseaseName,
            gemini_advice = adviceText
        )

        val apiService = PlantApiService.create(token)
        apiService.confirmDiary(predictionId!!, request).enqueue(object : retrofit2.Callback<GenericResponse> {
            override fun onResponse(call: retrofit2.Call<GenericResponse>, response: retrofit2.Response<GenericResponse>) {
                if (response.isSuccessful) {
                    Toast.makeText(this@ResultActivity, "紀錄已成功儲存！", Toast.LENGTH_SHORT).show()
                    btnSave.text = "已儲存"
                    Handler(Looper.getMainLooper()).postDelayed({
                        val intent = Intent(this@ResultActivity, HomeActivity::class.java)
                        intent.addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP or Intent.FLAG_ACTIVITY_NEW_TASK)
                        startActivity(intent)
                        finish()
                    }, 500)
                } else {
                    Toast.makeText(this@ResultActivity, "儲存失敗: ${response.code()}", Toast.LENGTH_SHORT).show()
                    btnSave.isEnabled = true
                    btnSave.text = "儲存至歷史病例"
                }
            }
            override fun onFailure(call: retrofit2.Call<GenericResponse>, t: Throwable) {
                Toast.makeText(this@ResultActivity, "網路連線失敗", Toast.LENGTH_SHORT).show()
                btnSave.isEnabled = true
                btnSave.text = "儲存至歷史病例"
            }
        })
    }

    override fun onResume() {
        super.onResume()
        ThemeManager.applyTheme(
            context = this,
            rootLayout = resultRoot,
            titles = listOf(tvMainTitle),
            mainButtons = listOf(btnSave),
            imageButtons = listOf(btnBack)
        )
    }

    private fun setupPipDragListener(imageUriString: String?) {
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

                        val maxContainerX = resultRoot.width - view.width
                        val maxContainerY = resultRoot.height - view.height

                        val safetyMargin = (20 * resources.displayMetrics.density).toInt()
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

                    if (!isDragging && event.action == MotionEvent.ACTION_UP) {
                        if (!imageUriString.isNullOrEmpty()) {
                            SoundManager.playBubblePop()
                            val intent = Intent(this, ImagePreviewActivity::class.java).apply {
                                putExtra("IMAGE_PATH", imageUriString)
                            }
                            startActivity(intent)
                        }
                    }
                }
            }
            true
        }
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
}