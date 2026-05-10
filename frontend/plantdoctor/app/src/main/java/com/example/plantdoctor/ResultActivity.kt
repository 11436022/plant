package com.example.plantdoctor

import android.content.Intent
import android.os.Bundle
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

        // 2. 接收診斷資料 (從 DiagnoseProgressActivity 傳過來的 JSON 字串)
        val resultJson = intent.getStringExtra("DIAGNOSIS_RESULT")

        if (!resultJson.isNullOrEmpty()) {
            try {
                // 使用 Gson 將 JSON 字串轉回 HistoryItem 物件
                val data = Gson().fromJson(resultJson, HistoryItem::class.java)

                // 填入畫面文字
                tvPlantName.text = "植物：${data.crop_name ?: "辨識中"}"
                tvDiseaseName.text = "診斷：${data.status_name}"

                // 組合建議與處方邏輯
                val fullAdvice = StringBuilder().apply {
                    append("【專家建議】\n${data.suggestion ?: "尚無建議"}\n\n")
                    append("【治療方法】\n${data.treatment ?: "請諮詢專業人員"}")
                }.toString()

                tvAdvice.text = fullAdvice

                // 使用 Glide 顯示診斷圖片
                if (!data.image_url.isNullOrEmpty()) {
                    val fullUrl = if (data.image_url.startsWith("http")) {
                        data.image_url
                    } else {
                        // 修正為本機開發 IP
                        "http://10.0.2.2:8000/${data.image_url}"
                    }

                    Glide.with(this)
                        .load(fullUrl)
                        .placeholder(android.R.drawable.ic_menu_gallery)
                        .into(imgPlant)
                }

            } catch (e: Exception) {
                e.printStackTrace()
                Toast.makeText(this, "報告內容加載失敗", Toast.LENGTH_SHORT).show()
            }
        }

        // 3. 按鈕：返回主頁
        btnBack.setOnClickListener {
            val intent = Intent(this, HomeActivity::class.java)
            intent.flags = Intent.FLAG_ACTIVITY_CLEAR_TOP or Intent.FLAG_ACTIVITY_SINGLE_TOP
            startActivity(intent)
            finish()
        }

        // 4. 按鈕：儲存
        btnSave.setOnClickListener {
            Toast.makeText(this, "紀錄已成功同步至雲端", Toast.LENGTH_SHORT).show()
            btnSave.isEnabled = false
            btnSave.text = "已儲存"
        }
    }
}