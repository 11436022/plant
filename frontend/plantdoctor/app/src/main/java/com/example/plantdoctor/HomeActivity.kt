package com.example.plantdoctor

import android.content.Intent
import android.os.Bundle
import android.widget.Button
import androidx.appcompat.app.AppCompatActivity

class HomeActivity : AppCompatActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        // 設定此 Activity 的佈局檔案為 activity_home.xml
        setContentView(R.layout.activity_home)

        // 找到佈局檔案中的各個按鈕 (Button)
        val btnDiagnose: Button = findViewById(R.id.btn_diagnose)
        val btnHistory: Button = findViewById(R.id.btn_history)
        val btnSettings: Button = findViewById(R.id.btn_settings)

        // 設定「診斷植物」按鈕的點擊事件
        btnDiagnose.setOnClickListener {
            // 正確流程：跳轉到讓使用者選擇拍照或上傳的 UploadActivity
            val intent = Intent(this, UploadActivity::class.java)
            startActivity(intent)
        }

        // 設定「歷史紀錄」按鈕的點擊事件
        btnHistory.setOnClickListener {
            val intent = Intent(this, HistoryListActivity::class.java)
            startActivity(intent)
        }

        // 設定「設定」按鈕的點擊事件
        btnSettings.setOnClickListener {
            val intent = Intent(this, SettingsActivity::class.java)
            startActivity(intent)
        }
    }
}