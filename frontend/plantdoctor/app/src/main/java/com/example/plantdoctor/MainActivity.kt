package com.example.plantdoctor

import android.content.Context
import android.content.Intent
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import androidx.appcompat.app.AppCompatActivity

class MainActivity : AppCompatActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        // 延遲三秒後，根據登入狀態決定跳轉到哪一個頁面
        Handler(Looper.getMainLooper()).postDelayed({
            val sharedPref = getSharedPreferences("PlantDoctor", Context.MODE_PRIVATE)
            val token = sharedPref.getString("token", null)

            if (token != null) {
                // 如果 token 存在，跳轉到主頁面
                val intent = Intent(this, HomeActivity::class.java)
                startActivity(intent)
            } else {
                // 如果 token 不存在，跳轉到登入頁面
                val intent = Intent(this, LoginActivity::class.java)
                startActivity(intent)
            }
            finish() // 關閉目前的啟動畫面
        }, 3000) // 3000 毫秒 = 3 秒
    }
}