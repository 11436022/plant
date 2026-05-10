package com.example.plantdoctor

import android.content.Context
import android.content.Intent
import android.os.Bundle
import android.widget.Button
import android.widget.EditText
import android.widget.ImageButton
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import retrofit2.Call
import retrofit2.Callback
import retrofit2.Response

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
        val tvForgotPassword = findViewById<TextView>(R.id.tv_forgot_password)
        val btnLogout = findViewById<Button>(R.id.btn_logout)

        // 將儲存的資料顯示在輸入框中
        etUsername.setText(savedUsername)
        etGmail.setText(savedEmail)



        // --- 3. 點擊事件處理 ---

        // 返回上一頁
        btnBack.setOnClickListener { finish() }

        // 忘記密碼 / 更改密碼
        tvForgotPassword.setOnClickListener {
            // 自動帶入當前已儲存的 Email
            showForgotPasswordDialog(savedEmail ?: "")
        }

        // 背景顏色選擇 (預留功能)
        findViewById<TextView>(R.id.tv_color_select).setOnClickListener {
            Toast.makeText(this, "功能開發中：背景顏色切換", Toast.LENGTH_SHORT).show()
        }

        // --- 4. 登出按鈕邏輯 ---
        btnLogout.setOnClickListener {
            // A. 清空所有登入資料
            with(sharedPref.edit()) {
                clear()
                apply()
            }

            Toast.makeText(this, "已成功登出", Toast.LENGTH_SHORT).show()

            // B. 跳回登入頁並清空堆疊
            val intent = Intent(this, LoginActivity::class.java)
            intent.flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
            startActivity(intent)
            finish()
        }
    }

    /**
     * 顯示忘記密碼彈窗
     */
    private fun showForgotPasswordDialog(currentEmail: String) {
        val builder = AlertDialog.Builder(this)
        builder.setTitle("重設密碼")
        builder.setMessage("系統將寄送重設連結至您的 Email：")

        val input = EditText(this)
        input.hint = "請輸入 Email"
        input.setText(currentEmail) // 自動填入目前帳號的 Email
        input.setPadding(50, 40, 50, 40)
        builder.setView(input)

        builder.setPositiveButton("送出") { _, _ ->
            val email = input.text.toString().trim()
            if (email.isNotEmpty()) {
                sendResetEmail(email)
            } else {
                Toast.makeText(this, "Email 不能為空", Toast.LENGTH_SHORT).show()
            }
        }
        builder.setNegativeButton("取消", null)
        builder.show()
    }

    /**
     * 呼叫 API 發送重設郵件
     */
    private fun sendResetEmail(email: String) {
        // 使用我們定義好的 ApiService (不需 Token)
        val apiService = PlantApiService.create(null)
        val request = ForgotPasswordRequest(email)

        apiService.forgotPassword(request).enqueue(object : Callback<GenericResponse> {
            override fun onResponse(call: Call<GenericResponse>, response: Response<GenericResponse>) {
                if (response.isSuccessful) {
                    Toast.makeText(this@SettingsActivity, "重設郵件已發送，請檢查您的信箱", Toast.LENGTH_LONG).show()
                } else {
                    Toast.makeText(this@SettingsActivity, "發送失敗，請確認 Email 是否正確", Toast.LENGTH_SHORT).show()
                }
            }

            override fun onFailure(call: Call<GenericResponse>, t: Throwable) {
                Toast.makeText(this@SettingsActivity, "網路連線失敗", Toast.LENGTH_SHORT).show()
            }
        })
    }
}