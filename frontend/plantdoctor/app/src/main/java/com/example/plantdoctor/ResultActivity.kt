package com.example.plantdoctor

import android.annotation.SuppressLint
import android.app.Dialog
import android.content.Context
import android.content.Intent
import android.content.res.ColorStateList
import android.graphics.Color
import android.graphics.drawable.ColorDrawable
import android.net.Uri
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.util.Log
import android.view.MotionEvent
import android.view.View
import android.view.ViewGroup
import android.view.Window
import android.widget.Button
import android.widget.FrameLayout
import android.widget.ImageButton
import android.widget.TextView
import android.widget.Toast
import androidx.activity.OnBackPressedCallback
import androidx.appcompat.app.AppCompatActivity
import androidx.cardview.widget.CardView
import com.bumptech.glide.Glide
import com.example.plantdoctor.databinding.ActivityResultBinding
import com.example.plantdoctor.databinding.DialogFeedbackBinding
import com.example.plantdoctor.databinding.DialogSaveConfirmBinding
import com.google.android.material.bottomsheet.BottomSheetBehavior
import com.google.gson.Gson
import retrofit2.Call
import retrofit2.Callback
import retrofit2.Response

class ResultActivity : AppCompatActivity() {

    private val windHandler = Handler(Looper.getMainLooper())
    private val windRunnable = Runnable {
        SoundManager.startWind()
    }

    private lateinit var binding: ActivityResultBinding

    private var imageUriString: String? = null
    private var plantName: String? = null
    private var diseaseName: String? = null
    private var isUnknownResult: Boolean = false

    private var dX = 0f
    private var dY = 0f
    private var startX = 0f
    private var startY = 0f
    private var isDragging = false

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityResultBinding.inflate(layoutInflater)
        setContentView(binding.root)

        // 2. BottomSheet 設定
        val behavior = BottomSheetBehavior.from(binding.cardAdvice)
        binding.tvTitle.post {
            val titleBottom = binding.tvTitle.bottom
            val marginPx = (10 * resources.displayMetrics.density).toInt()
            behavior.expandedOffset = titleBottom + marginPx
        }
        behavior.addBottomSheetCallback(object : BottomSheetBehavior.BottomSheetCallback() {
            override fun onStateChanged(bottomSheet: View, newState: Int) {
                if (newState == BottomSheetBehavior.STATE_EXPANDED) {
                    binding.cvPipContainer.visibility = View.VISIBLE
                    binding.cvPipContainer.alpha = 1f
                } else if (newState == BottomSheetBehavior.STATE_COLLAPSED) {
                    binding.cvPipContainer.visibility = View.GONE
                }
            }

            override fun onSlide(bottomSheet: View, slideOffset: Float) {
                if (slideOffset > 0.8f) {
                    binding.cvPipContainer.visibility = View.VISIBLE
                    binding.cvPipContainer.alpha = (slideOffset - 0.8f) * 5f
                } else {
                    binding.cvPipContainer.visibility = View.GONE
                }
            }
        })

        // 3. 接收資料並載入
        imageUriString = intent.getStringExtra("IMAGE_URI")
        val predictionId = intent.getStringExtra("PREDICTION_ID") // <-- 改回大寫，與 DiagnoseProgressActivity 保持一致
        val resultJson = intent.getStringExtra("ANALYSIS_RESULT_JSON")

        if (predictionId.isNullOrEmpty() || resultJson.isNullOrEmpty()) {
            Toast.makeText(this, "無法載入分析結果 (ID or JSON is null)", Toast.LENGTH_SHORT).show()
            finish()
            return
        }

        if (!imageUriString.isNullOrEmpty()) {
            val uri = Uri.parse(imageUriString)
            Glide.with(this).load(uri).into(binding.imgResultPlant)
            Glide.with(this).load(uri).into(binding.imgPipPlant)
        }

        try {
            val data = Gson().fromJson(resultJson, AnalysisResult::class.java)
            plantName = data.crop_name
            diseaseName = data.status_name
            binding.tvPlantName.text = "植物：${plantName ?: "無法辨識"}"
            binding.tvDiseaseName.text = "診斷：${diseaseName ?: "未知"}"

            val fullAdvice = StringBuilder().apply {
                append("【病症狀態】\n${data.suggestion ?: "尚無建議"}\n\n")
                append("【治療方法】\n${data.treatment ?: "請諮詢專業人員"}")
            }.toString()
            binding.tvAdvice.text = fullAdvice
            binding.tvAdvice.setTextIsSelectable(true)

            val unknownCrops = listOf("未知作物", "未知", "無法判定", "無法辨識", "非植物", "無植物特徵")
            val unknownStatuses = listOf("無法判定", "未知", "無植物特徵", "無法辨識", "非植物")
            isUnknownResult = (plantName.isNullOrEmpty() || plantName in unknownCrops
                    || diseaseName.isNullOrEmpty() || diseaseName in unknownStatuses
                    || data.category?.lowercase() in listOf("unknown", "invalid", "none"))

            if (isUnknownResult) {
                // 方案 A：無法判定或未知作物時，隱藏「儲存至日記」，只保留「結果有誤？（回饋）」選項
                binding.btnSave.visibility = View.GONE
                val params = binding.btnDiscard.layoutParams as android.widget.LinearLayout.LayoutParams
                params.marginEnd = 0
                binding.btnDiscard.layoutParams = params
                binding.btnDiscard.text = "結果有誤？（回饋）"
            } else {
                binding.btnSave.visibility = View.VISIBLE
                val marginPx = (8 * resources.displayMetrics.density).toInt()
                val params = binding.btnDiscard.layoutParams as android.widget.LinearLayout.LayoutParams
                params.marginEnd = marginPx
                binding.btnDiscard.layoutParams = params
                binding.btnDiscard.text = "結果有誤"
            }
        } catch (e: Exception) {
            e.printStackTrace()
            Toast.makeText(this, "報告內容解析失敗", Toast.LENGTH_SHORT).show()
        }

        // 4. 設定監聽事件
        setupPipDragListener(imageUriString)

        binding.imgResultPlant.setOnClickListener {
            if (!imageUriString.isNullOrEmpty()) {
                SoundManager.playBubblePop()
                val intent = Intent(this, ImagePreviewActivity::class.java).apply {
                    putExtra("IMAGE_PATH", imageUriString)
                }
                startActivity(intent)
            }
        }

        binding.btnBackHome.setOnClickListener {
            SoundManager.playBubblePop()
            if (isUnknownResult) {
                goToHome()
            } else {
                showSaveConfirmationDialog(predictionId)
            }
        }

        // 補上 "結果有誤" 按鈕的監聽器
        binding.btnDiscard.setOnClickListener {
            SoundManager.playBubblePop()
            showFeedbackDialog(predictionId)
        }

        // 補上 "儲存至日記" 按鈕的監聽器
        binding.btnSave.setOnClickListener {
            SoundManager.playBubblePop()
            confirmAndSaveDiary(predictionId)
        }

        // 註冊系統返回鍵監聽，確保 Android 13+ 預測性返回與實體返回鍵皆能正確觸發退出確認/關閉彈窗
        onBackPressedDispatcher.addCallback(this, object : OnBackPressedCallback(true) {
            override fun handleOnBackPressed() {
                val feedbackOverlay = binding.root.findViewById<FrameLayout>(R.id.layout_feedback_overlay)
                if (feedbackOverlay?.visibility == View.VISIBLE) {
                    feedbackOverlay.visibility = View.GONE
                    return
                }
                val saveOverlay = binding.root.findViewById<FrameLayout>(R.id.layout_save_overlay)
                if (saveOverlay?.visibility == View.VISIBLE) {
                    saveOverlay.visibility = View.GONE
                    return
                }
                if (isUnknownResult) {
                    goToHome()
                } else {
                    val currentPredId = intent.getStringExtra("PREDICTION_ID")
                    showSaveConfirmationDialog(currentPredId)
                }
            }
        })

        // 5. 啟動音效
        windHandler.postDelayed(windRunnable, 500)
    }

    override fun onResume() {
        super.onResume()
        ThemeManager.applyTheme(
            context = this,
            rootLayout = binding.root,
            titles = listOf(binding.tvTitle),
            mainButtons = listOf(binding.btnSave),
            imageButtons = listOf(binding.btnBackHome)
        )
        windHandler.postDelayed(windRunnable, 500)
    }

    override fun onDestroy() {
        super.onDestroy()
        windHandler.removeCallbacks(windRunnable)
        SoundManager.stopWind()
    }

    @Deprecated("Deprecated in Java")
    override fun onBackPressed() {
        val feedbackOverlay = binding.root.findViewById<FrameLayout>(R.id.layout_feedback_overlay)
        if (feedbackOverlay?.visibility == View.VISIBLE) {
            feedbackOverlay.visibility = View.GONE
            return
        }
        val saveOverlay = binding.root.findViewById<FrameLayout>(R.id.layout_save_overlay)
        if (saveOverlay?.visibility == View.VISIBLE) {
            saveOverlay.visibility = View.GONE
            return
        }
        if (isUnknownResult) {
            goToHome()
        } else {
            val predictionId = intent.getStringExtra("PREDICTION_ID")
            showSaveConfirmationDialog(predictionId)
        }
    }

    @SuppressLint("ClickableViewAccessibility")
    private fun setupPipDragListener(imageUriString: String?) {
        binding.cvPipContainer.setOnTouchListener { view, event ->
            when (event.action) {
                MotionEvent.ACTION_DOWN -> {
                    isDragging = false
                    dX = view.x - event.rawX
                    dY = view.y - event.rawY
                    startX = event.rawX
                    startY = event.rawY
                }
                MotionEvent.ACTION_MOVE -> {
                    val deltaX = event.rawX - startX
                    val deltaY = event.rawY - startY
                    if (isDragging || deltaX * deltaX + deltaY * deltaY > 20 * 20) {
                        isDragging = true
                        val newX = event.rawX + dX
                        val newY = event.rawY + dY
                        val parentWidth = (view.parent as View).width
                        val parentHeight = (view.parent as View).height
                        view.x = newX.coerceIn(0f, (parentWidth - view.width).toFloat())
                        view.y = newY.coerceIn(0f, (parentHeight - view.height).toFloat())
                    }
                }
                MotionEvent.ACTION_UP -> {
                    if (!isDragging) {
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

    private fun showSaveConfirmationDialog(predictionId: String?) {
        val overlay = binding.root.findViewById<FrameLayout>(R.id.layout_save_overlay) ?: return
        val cardRoot = overlay.findViewById<CardView>(R.id.included_save_dialog)
            ?: overlay.findViewById<CardView>(R.id.dialog_card_root)
        val btnClose = overlay.findViewById<ImageButton>(R.id.dialog_btn_close)
        val tvTitle = overlay.findViewById<TextView>(R.id.dialog_title)
        val tvMessage = overlay.findViewById<TextView>(R.id.dialog_message)
        val btnSave = overlay.findViewById<Button>(R.id.dialog_btn_save)
        val btnDontSave = overlay.findViewById<Button>(R.id.dialog_btn_dont_save)

        if (cardRoot != null && btnClose != null && tvTitle != null && tvMessage != null) {
            ThemeManager.applyThemeToDialog(
                this,
                cardRoot,
                btnClose,
                tvTitle,
                tvMessage
            )
        }

        overlay.visibility = View.VISIBLE

        btnClose?.setOnClickListener {
            SoundManager.playBubblePop()
            overlay.visibility = View.GONE
        }
        btnSave?.setOnClickListener {
            overlay.visibility = View.GONE
            confirmAndSaveDiary(predictionId)
        }
        btnDontSave?.setOnClickListener {
            overlay.visibility = View.GONE
            SoundManager.playBubblePop()
            goToHome()
        }
        overlay.setOnClickListener {
            SoundManager.playBubblePop()
            overlay.visibility = View.GONE
        }
        cardRoot?.setOnClickListener {
            // consume clicks to prevent closing
        }
    }

    private fun confirmAndSaveDiary(predictionId: String?) {
        if (isUnknownResult) {
            Toast.makeText(this, "未知作物或無法判定之結果，無法儲存至日記", Toast.LENGTH_SHORT).show()
            return
        }

        if (predictionId.isNullOrEmpty()) {
            Toast.makeText(this, "缺少預測ID，無法儲存", Toast.LENGTH_SHORT).show()
            return
        }

        val sharedPref = getSharedPreferences("PlantDoctor", Context.MODE_PRIVATE)
        val token = sharedPref.getString("token", null)
        if (token == null) {
            Toast.makeText(this, "請先登入", Toast.LENGTH_SHORT).show()
            startActivity(Intent(this, LoginActivity::class.java))
            finish()
            return
        }

        val userNote = binding.etUserNote.text.toString()

        binding.btnSave.isEnabled = false
        binding.btnSave.text = "儲存中..."

        // The server saves the diagnosis snapshot; display labels are not input.
        val request = DiaryConfirmRequest(user_note = userNote)

        val apiService = PlantApiService.create(token)
        apiService.confirmDiary(predictionId, request).enqueue(object : Callback<DiaryConfirmResponse> {
            override fun onResponse(call: Call<DiaryConfirmResponse>, response: Response<DiaryConfirmResponse>) {
                if (response.isSuccessful) {
                    Toast.makeText(this@ResultActivity, "紀錄已成功儲存！", Toast.LENGTH_SHORT).show()
                    binding.btnSave.text = "已儲存"
                    binding.btnSave.isEnabled = false
                    Handler(Looper.getMainLooper()).postDelayed({
                        if (!isFinishing && !isDestroyed) {
                            goToHome()
                        }
                    }, 800)
                } else {
                    val errorMsg = response.errorBody()?.string() ?: "未知錯誤"
                    Toast.makeText(this@ResultActivity, "儲存失敗: $errorMsg", Toast.LENGTH_LONG).show()
                    binding.btnSave.isEnabled = true
                    binding.btnSave.text = "儲存至日記"
                }
            }

            override fun onFailure(call: Call<DiaryConfirmResponse>, t: Throwable) {
                Toast.makeText(this@ResultActivity, "網路錯誤: ${t.message}", Toast.LENGTH_LONG).show()
                binding.btnSave.isEnabled = true
                binding.btnSave.text = "儲存至日記"
            }
        })
    }

    private fun showFeedbackDialog(predictionId: String?) {
        val overlay = binding.root.findViewById<FrameLayout>(R.id.layout_feedback_overlay) ?: return
        val cardRoot = overlay.findViewById<CardView>(R.id.included_feedback_dialog)
            ?: overlay.findViewById<CardView>(R.id.dialog_card_root)
        val btnClose = overlay.findViewById<ImageButton>(R.id.dialog_btn_close)
        val tvTitle = overlay.findViewById<TextView>(R.id.dialog_title)
        val tvMessage = overlay.findViewById<TextView>(R.id.dialog_message)
        val cbPlantError = overlay.findViewById<com.google.android.material.checkbox.MaterialCheckBox>(R.id.cb_plant_error)
        val cbDiseaseError = overlay.findViewById<com.google.android.material.checkbox.MaterialCheckBox>(R.id.cb_disease_error)
        val btnSubmit = overlay.findViewById<Button>(R.id.dialog_btn_submit)
        val btnCancel = overlay.findViewById<Button>(R.id.dialog_btn_cancel)

        if (cardRoot != null && btnClose != null && tvTitle != null && tvMessage != null) {
            ThemeManager.applyThemeToDialog(
                this,
                cardRoot,
                btnClose,
                tvTitle,
                tvMessage
            )
        }

        val sharedPref = getSharedPreferences("PlantDoctor", Context.MODE_PRIVATE)
        val themeId = sharedPref.getInt("THEME_COLOR_ID", 0)
        val cbTextColor = if (themeId == 0) Color.parseColor("#333333") else Color.WHITE
        cbPlantError?.setTextColor(cbTextColor)
        cbDiseaseError?.setTextColor(cbTextColor)

        cbPlantError?.isChecked = false
        cbDiseaseError?.isChecked = false

        val mainColorStr = when (themeId) {
            1 -> "#1565C0"
            2 -> "#D84315"
            3 -> "#AD1457"
            else -> "#2E7D32"
        }
        val mainColor = Color.parseColor(mainColorStr)
        btnSubmit?.backgroundTintList = ColorStateList.valueOf(mainColor)

        overlay.visibility = View.VISIBLE

        btnClose?.setOnClickListener {
            SoundManager.playBubblePop()
            overlay.visibility = View.GONE
        }

        btnCancel?.setOnClickListener {
            SoundManager.playBubblePop()
            overlay.visibility = View.GONE
        }

        btnSubmit?.setOnClickListener {
            SoundManager.playBubblePop()
            val isPlantError = cbPlantError?.isChecked == true
            val isDiseaseError = cbDiseaseError?.isChecked == true

            if (!isPlantError && !isDiseaseError) {
                Toast.makeText(this, "請至少勾選一項錯誤項目", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }

            overlay.visibility = View.GONE
            sendFeedback(predictionId, isPlantError = isPlantError, isDiseaseError = isDiseaseError)
        }

        overlay.setOnClickListener {
            SoundManager.playBubblePop()
            overlay.visibility = View.GONE
        }

        cardRoot?.setOnClickListener {
            // consume clicks to prevent closing
        }
    }

    private fun goToHome() {
        val intent = Intent(this, HomeActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_CLEAR_TOP or Intent.FLAG_ACTIVITY_SINGLE_TOP
        }
        startActivity(intent)
        finish()
    }

    private fun sendFeedback(predictionId: String?, isPlantError: Boolean, isDiseaseError: Boolean) {
        if (predictionId.isNullOrEmpty()) { // <-- 現在只檢查 predictionId
            Toast.makeText(this, "缺少預測ID，無法傳送回饋", Toast.LENGTH_SHORT).show()
            finish()
            return
        }

        val sharedPref = getSharedPreferences("PlantDoctor", Context.MODE_PRIVATE)
        val token = sharedPref.getString("token", null)
        if (token == null) {
            Toast.makeText(this, "請先登入", Toast.LENGTH_SHORT).show()
            finish()
            return
        }

        // 建立符合新 schema 的請求
        val request = DiagnosisFeedbackRequest(
            prediction_id = predictionId, // <-- 傳入 predictionId
            original_plant_name = plantName,
            original_disease_name = diseaseName,
            is_plant_error = isPlantError,
            is_disease_error = isDiseaseError
        )

        val apiService = PlantApiService.create(token)
        apiService.sendDiagnosisFeedback(request).enqueue(object : Callback<DiagnosisFeedbackResponse> {
            override fun onResponse(call: Call<DiagnosisFeedbackResponse>, response: Response<DiagnosisFeedbackResponse>) {
                if (response.isSuccessful) {
                    Toast.makeText(this@ResultActivity, "感謝您的回饋！我們將盡快改進。", Toast.LENGTH_LONG).show()
                } else {
                    val errorMsg = response.errorBody()?.string() ?: "未知錯誤"
                    Log.e("SendFeedback", "API Error: ${response.code()} - $errorMsg")
                    Toast.makeText(this@ResultActivity, "回饋傳送失敗: $errorMsg", Toast.LENGTH_LONG).show()
                }
                // 無論成功或失敗，都返回首頁
                goToHome()
            }

            override fun onFailure(call: Call<DiagnosisFeedbackResponse>, t: Throwable) {
                Log.e("SendFeedback", "Network Failure: ${t.message}", t)
                Toast.makeText(this@ResultActivity, "網路錯誤，無法傳送回饋", Toast.LENGTH_SHORT).show()
                // 無論成功或失敗，都返回首頁
                goToHome()
            }
        })
    }
}
