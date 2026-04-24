package com.example.plantdoctor

import android.content.Intent
import android.os.Bundle
import android.widget.Button
import android.widget.ImageButton
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity

class ResultActivity : AppCompatActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_result)

        // 綁定元件
        val btnBack = findViewById<ImageButton>(R.id.btn_back_home)
        val btnSave = findViewById<Button>(R.id.btn_save_report)

        // 1. 統一的返回邏輯
        btnBack.setOnClickListener {
            // 返回主頁面 (HomeActivity)
            val intent = Intent(this, HomeActivity::class.java)
            intent.flags = Intent.FLAG_ACTIVITY_CLEAR_TOP // 清除中間所有 Activity
            startActivity(intent)
            finish()
        }

        // 2. 儲存病例邏輯
        btnSave.setOnClickListener {
            // 模擬儲存成功
            Toast.makeText(this, "報告已儲存至您的病例庫", Toast.LENGTH_SHORT).show()

            // 儲存後也可以選擇自動跳轉回首頁
            btnSave.isEnabled = false
            btnSave.text = "已儲存"
        }
    }
}