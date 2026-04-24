package com.example.plantdoctor

import android.content.Intent
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import androidx.appcompat.app.AppCompatActivity

class MainActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        // 設定 2 秒 (2000毫秒) 後自動跳轉
        Handler(Looper.getMainLooper()).postDelayed({
            // 建立跳轉到 IntroActivity 的指令
            val intent = Intent(this, IntroActivity::class.java)
            startActivity(intent)

            // 結束這一頁，讓使用者無法按返回鍵回到封面
            finish()
        }, 2000)
    }
}