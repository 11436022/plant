package com.example.plantdoctor

import android.annotation.SuppressLint
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.util.Log
import android.view.MotionEvent
import android.view.View
import android.widget.Toast
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
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
                append("【專家建議】\n${data.suggestion ?: "尚無建議"}\n\n")
                append("【治療方法】\n${data.treatment ?: "請諮詢專業人員"}")
            }.toString()
            binding.tvAdvice.text = fullAdvice
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
            showSaveConfirmationDialog(predictionId)
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

        // 這個是舊的、隱藏的按鈕，可以保留或移除，但主要功能由 btn_save 取代
        binding.btnSaveReport.setOnClickListener {
            SoundManager.playBubblePop()
            confirmAndSaveDiary(predictionId)
        }

        // 5. 啟動音效
        windHandler.postDelayed(windRunnable, 500)
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
        apiService.confirmDiary(predictionId!!, request).enqueue(object : retrofit2.Callback<DiaryConfirmResponse> {
            override fun onResponse(call: retrofit2.Call<DiaryConfirmResponse>, response: retrofit2.Response<DiaryConfirmResponse>) {
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
            override fun onFailure(call: retrofit2.Call<DiaryConfirmResponse>, t: Throwable) {
                Toast.makeText(this@ResultActivity, "網路連線失敗", Toast.LENGTH_SHORT).show()
                btnSave.isEnabled = true
                btnSave.text = "儲存至歷史病例"
            }
        })
    }

    override fun onResume() {
        super.onResume()
        windHandler.postDelayed(windRunnable, 500)
    }

    override fun onDestroy() {
        super.onDestroy()
        windHandler.removeCallbacks(windRunnable)
        SoundManager.stopWind()
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
        val dialogBinding = DialogSaveConfirmBinding.inflate(layoutInflater)
        val builder = AlertDialog.Builder(this).setView(dialogBinding.root).setCancelable(true)
        val alertDialog = builder.create().apply {
            window?.setBackgroundDrawableResource(android.R.color.transparent)
            show()
        }

        ThemeManager.applyThemeToDialog(
            this,
            dialogBinding.dialogCardRoot,
            dialogBinding.dialogBtnClose,
            dialogBinding.dialogTitle,
            dialogBinding.dialogMessage
        )

        dialogBinding.dialogBtnClose.setOnClickListener {
            SoundManager.playBubblePop()
            alertDialog.dismiss()
        }
        dialogBinding.dialogBtnSave.setOnClickListener {
            alertDialog.dismiss()
            confirmAndSaveDiary(predictionId)
        }
        dialogBinding.dialogBtnDontSave.setOnClickListener {
            alertDialog.dismiss()
            SoundManager.playBubblePop()
            showFeedbackDialog(predictionId)
        }
    }

    private fun confirmAndSaveDiary(predictionId: String?) {
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
        val adviceText = binding.tvAdvice.text.toString()
        val currentDiseaseName = diseaseName

        if (currentDiseaseName.isNullOrEmpty()) {
            Toast.makeText(this, "診斷結果不完整，無法儲存", Toast.LENGTH_SHORT).show()
            return
        }

        binding.btnSaveReport.isEnabled = false
        binding.btnSaveReport.text = "儲存中..."

        val request = DiaryConfirmRequest(
            user_note = userNote,
            disease_name = currentDiseaseName,
            gemini_advice = adviceText
        )

        val apiService = PlantApiService.create(token)
        apiService.confirmDiary(predictionId, request).enqueue(object : Callback<GenericResponse> {
            override fun onResponse(call: Call<GenericResponse>, response: Response<GenericResponse>) {
                if (response.isSuccessful) {
                    Toast.makeText(this@ResultActivity, "紀錄已成功儲存！", Toast.LENGTH_SHORT).show()
                    binding.btnSaveReport.text = "已儲存"
                    Handler(Looper.getMainLooper()).postDelayed({
                        val intent = Intent(this@ResultActivity, HomeActivity::class.java)
                        intent.flags = Intent.FLAG_ACTIVITY_CLEAR_TOP or Intent.FLAG_ACTIVITY_NEW_TASK
                        startActivity(intent)
                        finish()
                    }, 1000)
                } else {
                    Toast.makeText(this@ResultActivity, "儲存失敗: ${response.errorBody()?.string()}", Toast.LENGTH_LONG).show()
                    binding.btnSaveReport.isEnabled = true
                    binding.btnSaveReport.text = "儲存至日記"
                }
            }

            override fun onFailure(call: Call<GenericResponse>, t: Throwable) {
                Toast.makeText(this@ResultActivity, "網路錯誤: ${t.message}", Toast.LENGTH_LONG).show()
                binding.btnSaveReport.isEnabled = true
                binding.btnSaveReport.text = "儲存至日記"
            }
        })
    }

    private fun showFeedbackDialog(predictionId: String?) {
        val dialogBinding = DialogFeedbackBinding.inflate(layoutInflater)
        AlertDialog.Builder(this)
            .setView(dialogBinding.root)
            .setTitle("結果有誤？")
            .setMessage("請告訴我們是哪個部分出錯了，這能幫助我們未來提供更準確的分析！")
            .setCancelable(true)
            .setPositiveButton("送出") { _, _ ->
                val isPlantError = dialogBinding.cbPlantError.isChecked
                val isDiseaseError = dialogBinding.cbDiseaseError.isChecked

                if (isPlantError || isDiseaseError) {
                    sendFeedback(predictionId, isPlantError = isPlantError, isDiseaseError = isDiseaseError)
                } else {
                    Toast.makeText(this, "您未選擇任何項目，即將返回首頁", Toast.LENGTH_SHORT).show()
                    goToHome()
                }
            }
            .setNegativeButton("取消") { _, _ ->
                goToHome()
            }
            .show()
    }

    private fun goToHome() {
        val intent = Intent(this, HomeActivity::class.java)
        intent.flags = Intent.FLAG_ACTIVITY_CLEAR_TOP or Intent.FLAG_ACTIVITY_NEW_TASK
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

    /*
    private fun saveDiagnosisResult() {
        val userNote = "" // 筆記功能已在新版介面移除，暫時傳入空字串

        if (plantName == null || diseaseName == null || advice == null || imageUrl == null) {
            Toast.makeText(this, "診斷結果不完整，無法儲存", Toast.LENGTH_SHORT).show()
            return
        }

        val request = DiaryEntry.DiaryEntryRequest(
            plant_name = plantName!!,
            disease = diseaseName!!,
            treatment_suggestion = advice!!,
            notes = userNote,
            image_url = imageUrl!!
        )

        plantApiService.addDiaryEntry(request).enqueue(object : Callback<DiaryEntry> {
            override fun onResponse(call: Call<DiaryEntry>, response: Response<DiaryEntry>) {
                if (response.isSuccessful) {
                    Toast.makeText(this@ResultActivity, "成功儲存至日記", Toast.LENGTH_SHORT).show()
                    finish() // 關閉此 Activity，返回主畫面
                } else {
                    Toast.makeText(this@ResultActivity, "儲存失敗: ${response.errorBody()?.string()}", Toast.LENGTH_LONG).show()
                }
            }

            override fun onFailure(call: Call<DiaryEntry>, t: Throwable) {
                Toast.makeText(this@ResultActivity, "網路錯誤: ${t.message}", Toast.LENGTH_LONG).show()
            }
        })
    }
    */


}