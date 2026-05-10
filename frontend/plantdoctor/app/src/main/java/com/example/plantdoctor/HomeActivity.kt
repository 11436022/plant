package com.example.plantdoctor

import android.content.Intent
import android.os.Bundle
import android.widget.Button
import androidx.appcompat.app.AppCompatActivity

class HomeActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_home)

        val btnSettings = findViewById<Button>(R.id.btn_settings)
        val btnDiagnose = findViewById<Button>(R.id.btn_diagnose)
        val btnHistory = findViewById<Button>(R.id.btn_history)

        // 1. 點擊「個人設定」
        btnSettings.setOnClickListener {
            val intent = Intent(this, SettingsActivity::class.java)
            startActivity(intent)
        }

        // 2. 點擊「診斷植物」 (對應到你清單中的 UploadActivity)
        btnDiagnose.setOnClickListener {
            val intent = Intent(this, UploadActivity::class.java)
            startActivity(intent)
        }

        // 3. 點擊「查詢病例」 (對應到你清單中的 HistoryProgressActivity)
        btnHistory.setOnClickListener {
            val intent = Intent(this, HistoryProgressActivity::class.java)
            startActivity(intent)
        }
    }
}