package com.example.plantdoctor

import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.view.MotionEvent
import android.util.Log
import android.widget.Button
import android.widget.EditText
import android.widget.ImageButton
import android.widget.ImageView
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
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

        // 1. 綁定元件
        val btnBack = findViewById<ImageButton>(R.id.btn_back_home)
        val btnSave = findViewById<Button>(R.id.btn_save_report)
        val tvPlantName = findViewById<TextView>(R.id.tv_plant_name)
        val tvDiseaseName = findViewById<TextView>(R.id.tv_disease_name)
        val tvAdvice = findViewById<TextView>(R.id.tv_advice)
        val imgPlant = findViewById<ImageView>(R.id.img_result_plant)

        // 🌟 重新改回綁定 EditText (注意組員原稿是轉成 EditText 格式)
        val etUserNote = findViewById<EditText>(R.id.et_user_note)

        // 2. 接收資料並使用 Glide 載入
        val imageUriString = intent.getStringExtra("IMAGE_URI")
        val predictionId = intent.getStringExtra("PREDICTION_ID")
        val resultJson = intent.getStringExtra("ANALYSIS_RESULT_JSON")

        if (!imageUriString.isNullOrEmpty()) {
            Glide.with(this)
                .load(Uri.parse(imageUriString))
                .into(imgPlant)
        }

        // 🌟 核心新增：點擊植物照片進入全螢幕放大查看！
        imgPlant.setOnClickListener {
            if (!imageUriString.isNullOrEmpty()) {
                SoundManager.playBubblePop() // 播放音效
                val intent = Intent(this, ImagePreviewActivity::class.java).apply {
                    putExtra("IMAGE_PATH", imageUriString) // 把圖片路徑打包帶走
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

        // 4. 按鈕：【恢復組員連網功能】並附加療癒音效
        btnSave.setOnClickListener {
            // 點擊瞬間播放泡泡聲
            SoundManager.playBubblePop()

            btnSave.isEnabled = false
            btnSave.text = "儲存中..."

            // 從改回來的 etUserNote 獲取內容
            val userNote = etUserNote.text.toString()

            val sharedPref = getSharedPreferences("PlantDoctor", MODE_PRIVATE)
            val token = sharedPref.getString("token", null)

            if (token == null) {
                Toast.makeText(this, "請先登入", Toast.LENGTH_SHORT).show()
                btnSave.isEnabled = true
                btnSave.text = "存入日記"
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
                        btnSave.text = "存入日記"
                    }
                }

                override fun onFailure(call: retrofit2.Call<GenericResponse>, t: Throwable) {
                    Toast.makeText(this@ResultActivity, "網路連線失敗", Toast.LENGTH_SHORT).show()
                    btnSave.isEnabled = true
                    btnSave.text = "存入日記"
                }
            })
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