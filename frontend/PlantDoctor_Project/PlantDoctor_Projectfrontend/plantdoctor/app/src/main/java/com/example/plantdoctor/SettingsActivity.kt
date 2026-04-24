package com.example.plantdoctor

import android.content.Context
import android.content.Intent
import android.os.Bundle
import android.widget.Button
import android.widget.EditText
import android.widget.ImageButton
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity

class SettingsActivity : AppCompatActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_settings)

        // --- 1. 取得 SharedPreferences 資料 ---
        val sharedPref = getSharedPreferences("PlantDoctor", Context.MODE_PRIVATE)
        val savedUsername = sharedPref.getString("username", "尚未登錄")
        val savedEmail = sharedPref.getString("email", "尚未設定 Email")

        // --- 2. 綁定 UI 並顯示資料 ---
        val btnBack = findViewById<ImageButton>(R.id.btn_back_home)
        val etUsername = findViewById<EditText>(R.id.et_username)
        val etGmail = findViewById<EditText>(R.id.et_gmail)

        // 將儲存的資料顯示在輸入框中 (setText)
        etUsername.setText(savedUsername)
        etGmail.setText(savedEmail)

        // --- 3. 點擊事件處理 ---

        // 返回上一頁 (Home)
        btnBack.setOnClickListener {
            finish()
        }

        // 忘記密碼
        findViewById<TextView>(R.id.tv_forgot_password).setOnClickListener {
            Toast.makeText(this, "正在導向密碼重設頁面...", Toast.LENGTH_SHORT).show()
        }

        // 背景顏色選擇
        findViewById<TextView>(R.id.tv_color_select).setOnClickListener {
            Toast.makeText(this, "功能開發中：背景顏色切換", Toast.LENGTH_SHORT).show()
        }

        // --- 4. 登出按鈕邏輯 (新增) ---
        // 假設你的 XML 裡有一個登出按鈕，ID 為 btn_logout
        val btnLogout = findViewById<Button>(R.id.btn_logout)
        btnLogout.setOnClickListener {
            // A. 清空小本本資料
            with(sharedPref.edit()) {
                clear() // 清除所有存儲內容 (包括 is_logged_in, token, username 等)
                apply()
            }

            // B. 顯示提示
            Toast.makeText(this, "已成功登出", Toast.LENGTH_SHORT).show()

            // C. 跳回登錄頁並清空所有頁面堆疊
            val intent = Intent(this, LoginActivity::class.java)
            // 這兩行非常重要，確保按「返回鍵」不會再回到設定頁
            intent.flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
            startActivity(intent)
            finish()
        }
    }
}