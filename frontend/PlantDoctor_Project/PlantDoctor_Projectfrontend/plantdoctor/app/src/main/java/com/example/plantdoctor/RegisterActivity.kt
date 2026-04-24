package com.example.plantdoctor

import android.content.Context
import android.content.Intent
import android.os.Bundle
import android.util.Log
import android.widget.Button
import android.widget.EditText
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import okhttp3.ResponseBody
import retrofit2.Call
import retrofit2.Callback
import retrofit2.Response

class RegisterActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_register)

        // 1. 取得所有輸入框 (請確認 ID 與 XML 檔案一致)
        val edtUsername = findViewById<EditText>(R.id.et_reg_username)
        val edtPassword = findViewById<EditText>(R.id.et_reg_password)
        val edtEmail = findViewById<EditText>(R.id.et_reg_gmail)
        val btnSubmit = findViewById<Button>(R.id.btn_register_submit)
        val tvBackLogin = findViewById<TextView>(R.id.tv_back_to_login)

        val apiService = PlantApiService.create()

        btnSubmit.setOnClickListener {
            val username = edtUsername.text.toString().trim()
            val password = edtPassword.text.toString().trim()
            val email = edtEmail.text.toString().trim()

            // 2. 基本防呆檢查
            if (username.isEmpty() || password.isEmpty() || email.isEmpty()) {
                Toast.makeText(this, "帳號、密碼和 Email 都要填寫喔！", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }

            // 3. 建立註冊資料
            // 註：這裡的 RegisterRequest 欄位名稱需與 PlantApiService.kt 中定義的一致
            val regData = RegisterRequest(
                username = username,
                password = password,
                email = email,
                full_name = username // 姓名暫時設為與帳號相同
            )

            // 4. 呼叫 API
            apiService.register(regData).enqueue(object : Callback<ResponseBody> {
                override fun onResponse(call: Call<ResponseBody>, response: Response<ResponseBody>) {
                    if (response.isSuccessful) {

                        // --- 【關鍵：註冊成功後存入小本本】 ---
                        val sharedPref = getSharedPreferences("PlantDoctor", Context.MODE_PRIVATE)
                        with(sharedPref.edit()) {
                            putBoolean("is_logged_in", true)   // 標記為已登入
                            putString("username", username)     // 存入帳號
                            putString("email", email)           // 存入 Email
                            apply()
                        }

                        Toast.makeText(this@RegisterActivity, "註冊成功！", Toast.LENGTH_SHORT).show()

                        // 跳轉到主頁，並清空之前的 Activity 堆疊，避免返回後又看到註冊頁
                        val intent = Intent(this@RegisterActivity, HomeActivity::class.java)
                        intent.flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
                        startActivity(intent)
                        finish()

                    } else {
                        val errorDetail = response.errorBody()?.string()
                        Log.e("RegisterActivity", "Error: $errorDetail")
                        Toast.makeText(this@RegisterActivity, "註冊失敗：帳號或 Email 可能已被使用", Toast.LENGTH_SHORT).show()
                    }
                }

                override fun onFailure(call: Call<ResponseBody>, t: Throwable) {
                    Log.e("RegisterActivity", "Failure: ${t.message}")
                    Toast.makeText(this@RegisterActivity, "網路連線失敗，請檢查後端狀態", Toast.LENGTH_SHORT).show()
                }
            })
        }

        // 返回登錄頁面
        tvBackLogin.setOnClickListener {
            finish()
        }
    }
}