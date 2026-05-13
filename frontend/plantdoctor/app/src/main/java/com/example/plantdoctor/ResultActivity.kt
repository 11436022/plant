package com.example.plantdoctor

import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.util.Log
import android.widget.Button
import android.widget.ImageButton
import android.widget.ImageView
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import com.bumptech.glide.Glide
import com.google.gson.Gson

class ResultActivity : AppCompatActivity() {

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

        // 2. 接收【新流程】的資料
        val imageUriString = intent.getStringExtra("IMAGE_URI") // <-- 新增：接收圖片 URI
        val predictionId = intent.getStringExtra("PREDICTION_ID")
        val resultJson = intent.getStringExtra("ANALYSIS_RESULT_JSON")

        // 使用 Glide 載入本地圖片
        if (!imageUriString.isNullOrEmpty()) {
            Glide.with(this)
                .load(Uri.parse(imageUriString))
                .into(imgPlant)
        }

        if (predictionId.isNullOrEmpty() || resultJson.isNullOrEmpty()) {
            Toast.makeText(this, "無法載入分析結果", Toast.LENGTH_SHORT).show()
            finish()
            return
        }

        // 【偵錯用】
        Log.d("DEBUG_ID", "Received Prediction ID: $predictionId")
        Log.d("DEBUG_JSON", "Received JSON: $resultJson")

        try {
            // 使用 Gson 將 JSON 字串轉回 AnalysisResult 物件
            val data = Gson().fromJson(resultJson, AnalysisResult::class.java)

            // 填入畫面文字
            tvPlantName.text = "植物：${data.crop_name ?: "無法辨識"}"
            tvDiseaseName.text = "診斷：${data.status_name ?: "未知"}"

            val fullAdvice = StringBuilder().apply {
                append("【專家建議】\n${data.suggestion ?: "尚無建議"}\n\n")
                append("【治療方法】\n${data.treatment ?: "請諮詢專業人員"}")
            }.toString()
            tvAdvice.text = fullAdvice

            // 注意：由於 predict API 不直接回傳可公開訪問的 image_url，
            // 這裡我們暫時不處理圖片顯示。若要顯示，需從 DiagnoseProgressActivity 傳遞原始 URI。

        } catch (e: Exception) {
            e.printStackTrace()
            Toast.makeText(this, "報告內容解析失敗", Toast.LENGTH_SHORT).show()
        }


        // 3. 按鈕：返回主頁
        btnBack.setOnClickListener {
            val intent = Intent(this, HomeActivity::class.java)
            intent.flags = Intent.FLAG_ACTIVITY_CLEAR_TOP or Intent.FLAG_ACTIVITY_SINGLE_TOP
            startActivity(intent)
            finish()
        }

        // 4. 按鈕：【新流程】確認儲存
        btnSave.setOnClickListener {
            // 禁用按鈕，防止重複點擊
            btnSave.isEnabled = false
            btnSave.text = "儲存中..."

            // 【新增】從 EditText 獲取使用者筆記
            val userNote = findViewById<TextView>(R.id.et_user_note).text.toString()

            val sharedPref = getSharedPreferences("PlantDoctor", MODE_PRIVATE)
            val token = sharedPref.getString("token", null)

            if (token == null) {
                Toast.makeText(this, "請先登入", Toast.LENGTH_SHORT).show()
                btnSave.isEnabled = true
                btnSave.text = "存入日記"
                return@setOnClickListener
            }

            val apiService = PlantApiService.create(token)
            // 【修改】將使用者筆記放入請求中
            val request = ConfirmRequest(user_note = userNote)

            apiService.confirmDiary(predictionId, request).enqueue(object : retrofit2.Callback<GenericResponse> {
                override fun onResponse(call: retrofit2.Call<GenericResponse>, response: retrofit2.Response<GenericResponse>) {
                    if (response.isSuccessful) {
                        Toast.makeText(this@ResultActivity, "紀錄已成功儲存！", Toast.LENGTH_SHORT).show()
                        btnSave.text = "已儲存"
                        // 儲存成功後，可以考慮直接跳轉到歷史列表
                        // startActivity(Intent(this@ResultActivity, HistoryListActivity::class.java))
                        // finish()
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
    }
}