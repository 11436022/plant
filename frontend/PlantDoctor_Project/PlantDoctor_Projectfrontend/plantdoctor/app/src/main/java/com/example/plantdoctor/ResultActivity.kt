package com.example.plantdoctor

import android.content.Intent
import android.os.Bundle
import android.widget.Button
import android.widget.ImageButton
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import org.json.JSONObject

class ResultActivity : AppCompatActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_result)

        // 1. 綁定元件 (對應你的 XML ID)
        val btnBack = findViewById<ImageButton>(R.id.btn_back_home)
        val btnSave = findViewById<Button>(R.id.btn_save_report)
        val tvDiseaseName = findViewById<TextView>(R.id.tv_disease_name) // 修正 ID
        val tvAdvice = findViewById<TextView>(R.id.tv_advice)           // 修正 ID

        // 2. 接收診斷資料
        val resultJson = intent.getStringExtra("DIAGNOSIS_RESULT")

        if (resultJson != null) {
            try {
                val jsonObject = JSONObject(resultJson)
                if (jsonObject.getString("status") == "success") {
                    val data = jsonObject.getJSONObject("data")

                    // 抓取真實資料
                    val statusName = data.optString("status_name", "未知狀態")
                    val suggestion = data.optString("suggestion", "")
                    val treatment = data.optString("treatment", "")

                    // 填入畫面
                    tvDiseaseName.text = "患病：$statusName"

                    // 把建議和處理方法組合在一起顯示
                    val fullAdvice = "【建議】\n$suggestion\n\n【處方】\n$treatment"
                    tvAdvice.text = fullAdvice
                }
            } catch (e: Exception) {
                e.printStackTrace()
                Toast.makeText(this, "解析結果失敗", Toast.LENGTH_SHORT).show()
            }
        }

        // 3. 返回邏輯
        btnBack.setOnClickListener {
            val intent = Intent(this, HomeActivity::class.java)
            intent.flags = Intent.FLAG_ACTIVITY_CLEAR_TOP
            startActivity(intent)
            finish()
        }

        // 4. 儲存邏輯
        btnSave.setOnClickListener {
            Toast.makeText(this, "報告已儲存至您的病例庫", Toast.LENGTH_SHORT).show()
            btnSave.isEnabled = false
            btnSave.text = "已儲存"
        }
    }
}