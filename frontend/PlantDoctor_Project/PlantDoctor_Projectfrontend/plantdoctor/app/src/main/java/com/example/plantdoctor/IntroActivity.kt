package com.example.plantdoctor

import android.content.Intent
import android.os.Bundle
import android.widget.Button
import androidx.appcompat.app.AppCompatActivity

class IntroActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_intro)

        // 1. 找到畫面上的按鈕
        val btnStart = findViewById<Button>(R.id.btn_start)

        // 2. 設定按鈕的點擊指令
        btnStart.setOnClickListener {
            // 當按鈕被點擊時，執行跳轉
            val intent = Intent(this, LoginActivity::class.java)
            startActivity(intent)

            // 可選：如果你希望跳轉後有音效，可以在這裡預留播放指令

            finish() // 關閉介紹頁
        }
    }
}