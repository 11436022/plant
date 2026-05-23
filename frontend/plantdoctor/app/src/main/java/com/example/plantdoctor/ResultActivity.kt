package com.example.plantdoctor

import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.view.MotionEvent
import android.util.Log
import android.view.View
import android.widget.LinearLayout
import android.widget.Button
import android.widget.EditText
import android.widget.ImageButton
import android.widget.ImageView
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.constraintlayout.widget.ConstraintLayout
import com.bumptech.glide.Glide
import com.google.gson.Gson



class ResultActivity : AppCompatActivity() {
    private val windHandler = Handler(Looper.getMainLooper())
    private val windRunnable = Runnable {
        SoundManager.startWind()
    }
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_result)
// 🌟 事先宣告全域偏好設定，供下方所有按鈕與引導元件共用，徹底根除 Unresolved sharedPref 錯誤
        val sharedPref = getSharedPreferences("PlantDoctor", MODE_PRIVATE)
// 1. 綁定元件
        val resultRoot = findViewById<ConstraintLayout>(R.id.result_root_layout)
        val btnBack = findViewById<ImageButton>(R.id.btn_back_home)
        val btnSave = findViewById<Button>(R.id.btn_save_report)
        val tvPlantName = findViewById<TextView>(R.id.tv_plant_name)
        val tvDiseaseName = findViewById<TextView>(R.id.tv_disease_name)
        val tvAdvice = findViewById<TextView>(R.id.tv_advice)
        val imgPlant = findViewById<ImageView>(R.id.img_result_plant)

        // 🌟 綁定新的 EditText ID
        val etUserNote = findViewById<EditText>(R.id.et_user_note_edit)

        // --- 強制設定使用者筆記區塊為「編輯模式」 ---
        val layoutNoteDisplay = findViewById<LinearLayout>(R.id.layout_note_display)
        val layoutNoteEdit = findViewById<LinearLayout>(R.id.layout_note_edit)
        layoutNoteDisplay.visibility = View.GONE
        layoutNoteEdit.visibility = View.VISIBLE
        // -----------------------------------------

// 2. 接收資料並使用 Glide 載入
        val imageUriString = intent.getStringExtra("IMAGE_URI")
        val predictionId = intent.getStringExtra("PREDICTION_ID")
        val resultJson = intent.getStringExtra("ANALYSIS_RESULT_JSON")
        if (!imageUriString.isNullOrEmpty()) {
            Glide.with(this)
                .load(Uri.parse(imageUriString))
                .into(imgPlant)
        }

// 點擊植物照片進入全螢幕放大查看
        imgPlant.setOnClickListener {
            if (!imageUriString.isNullOrEmpty()) {
                SoundManager.playBubblePop()
                val intent = Intent(this, ImagePreviewActivity::class.java).apply {
                    putExtra("IMAGE_PATH", imageUriString)
                }
                startActivity(intent)
            }
        }

        if (predictionId.isNullOrEmpty() || resultJson.isNullOrEmpty()) {
            Toast.makeText(this, "無法載入分析結果", Toast.LENGTH_SHORT).show()
            finish()
            return
        }

        Log.d("DEBUG_ID", "Received Prediction ID: $predictionId")
        Log.d("DEBUG_JSON", "Received JSON: $resultJson")

        try {
            val data = Gson().fromJson(resultJson, AnalysisResult::class.java)
            tvPlantName.text = "植物：${data.crop_name ?: "無法辨識"}"
            tvDiseaseName.text = "診斷：${data.status_name ?: "未知"}"
            val fullAdvice = StringBuilder().apply {
                append("【專家建議】\n${data.suggestion ?: "尚無建議"}\n\n")
                append("【治療方法】\n${data.treatment ?: "請諮詢專業人員"}")
            }.toString()
            tvAdvice.text = fullAdvice
        } catch (e: Exception) {
            e.printStackTrace()
            Toast.makeText(this, "報告內容解析失敗", Toast.LENGTH_SHORT).show()
        }

// 3. 按鈕：返回主頁
        btnBack.setOnClickListener {
            SoundManager.playBubblePop()
            val intent = Intent(this, HomeActivity::class.java)
            intent.flags = Intent.FLAG_ACTIVITY_CLEAR_TOP or Intent.FLAG_ACTIVITY_SINGLE_TOP
            startActivity(intent)
            finish()
        }

// 4. 按鈕：存入日記功能
        btnSave.setOnClickListener {
            SoundManager.playBubblePop()
            btnSave.isEnabled = false
            btnSave.text = "儲存中..."
            val userNote = etUserNote.text.toString()
            val token = sharedPref.getString("token", null)
            if (token == null) {
                Toast.makeText(this, "請先登入", Toast.LENGTH_SHORT).show()
                btnSave.isEnabled = true
                btnSave.text = "儲存至歷史病例"
                return@setOnClickListener
            }
            val apiService = PlantApiService.create(token)
            val request = ConfirmRequest(user_note = userNote)
            apiService.confirmDiary(predictionId, request).enqueue(object : retrofit2.Callback<GenericResponse> {
                override fun onResponse(call: retrofit2.Call<GenericResponse>, response: retrofit2.Response<GenericResponse>) {
                    if (response.isSuccessful) {
                        Toast.makeText(this@ResultActivity, "紀錄已成功儲存！", Toast.LENGTH_SHORT).show()
                        btnSave.text = "已儲存"
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
// ==========================================================
// 🌟 新手引導：診斷報告頁 3秒自動接力完全體
// ==========================================================
        val isFirstTimeResult = sharedPref.getBoolean("IS_FIRST_TIME_RESULT", true)
        if (isFirstTimeResult) {
            val targetColorRes = android.R.color.holo_green_dark
            val autoJumpHandler = Handler(Looper.getMainLooper())
            var targetView1: com.getkeepsafe.taptargetview.TapTargetView? = null
            var targetView2: com.getkeepsafe.taptargetview.TapTargetView? = null
            var hasMovedToStep2 = false
            val jumpToStep2Runnable = Runnable { targetView1?.dismiss(true) }
            val finishSequenceRunnable = Runnable { targetView2?.dismiss(true) }

// 第二步：介紹 AI 醫生處方箋
            val startStep2 = {
                if (!hasMovedToStep2) {
                    hasMovedToStep2 = true
                    SoundManager.playBubblePop()
                    targetView2 = com.getkeepsafe.taptargetview.TapTargetView.showFor(this,
                        com.getkeepsafe.taptargetview.TapTarget.forView(
                            tvAdvice, "第二步：AI 醫生處方箋", "這裡會顯示詳細的病害分析、澆水與除蟲建議，幫你對症下藥！"
                        ).outerCircleColor(targetColorRes)
                            .targetCircleColor(android.R.color.white)
                            .titleTextSize(24)
                            .descriptionTextSize(16)
                            .textColor(android.R.color.white)
                            .transparentTarget(true)
                            .drawShadow(true)
                            .cancelable(false),
                        object : com.getkeepsafe.taptargetview.TapTargetView.Listener() {
                            override fun onTargetClick(view: com.getkeepsafe.taptargetview.TapTargetView?) {
                                super.onTargetClick(view)
                                autoJumpHandler.removeCallbacks(finishSequenceRunnable)
                                sharedPref.edit().putBoolean("IS_FIRST_TIME_RESULT", false).apply()
                            }
                            override fun onTargetDismissed(view: com.getkeepsafe.taptargetview.TapTargetView?, userInitiated: Boolean) {
                                super.onTargetDismissed(view, userInitiated)
                                sharedPref.edit().putBoolean("IS_FIRST_TIME_RESULT", false).apply()
                            }
                        }
                    )
                    autoJumpHandler.postDelayed(finishSequenceRunnable, 3000)
                }
            }
// 第一步：提示可以雙指縮放圖片
            targetView1 = com.getkeepsafe.taptargetview.TapTargetView.showFor(this,
                com.getkeepsafe.taptargetview.TapTarget.forView(
                    imgPlant, "第一步：雙指縮放看細節", "你可以用兩隻手指放大或縮小這張病害照片，仔細觀察植物微觀病徵！"
                ).outerCircleColor(targetColorRes)
                    .targetCircleColor(android.R.color.white)
                    .titleTextSize(24)
                    .descriptionTextSize(16)
                    .textColor(android.R.color.white)
                    .transparentTarget(true)
                    .drawShadow(true)
                    .cancelable(false),
                object : com.getkeepsafe.taptargetview.TapTargetView.Listener() {
                    override fun onTargetClick(view: com.getkeepsafe.taptargetview.TapTargetView?) {
                        super.onTargetClick(view)
                        autoJumpHandler.removeCallbacks(jumpToStep2Runnable)
                        startStep2()
                    }
                    override fun onTargetDismissed(view: com.getkeepsafe.taptargetview.TapTargetView?, userInitiated: Boolean) {
                        super.onTargetDismissed(view, userInitiated)
                        startStep2()
                    }
                }
            )
            autoJumpHandler.postDelayed(jumpToStep2Runnable, 3000)
        }
    } // onCreate 結尾

    override fun onTouchEvent(event: MotionEvent?): Boolean {
        if (event != null) {
            when (event.action) {
                MotionEvent.ACTION_DOWN -> {
                    windHandler.postDelayed(windRunnable, 500)
                }
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