package com.example.plantdoctor

import android.content.Context
import android.os.Bundle
import android.util.Log
import android.widget.Button
import android.widget.EditText
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import retrofit2.Call
import retrofit2.Callback
import retrofit2.Response

class RegisterActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_register)

        val edtUsername = findViewById<EditText>(R.id.et_reg_username)
        val edtPassword = findViewById<EditText>(R.id.et_reg_password)
        val edtEmail = findViewById<EditText>(R.id.et_reg_gmail)
        val btnSubmit = findViewById<Button>(R.id.btn_register_submit)
        val tvBackLogin = findViewById<TextView>(R.id.tv_back_to_login)

        // 註冊時不需要 Token，所以傳 null 建立 API Service
        val apiService = PlantApiService.create(null)

        btnSubmit.setOnClickListener {
            val username = edtUsername.text.toString().trim()
            val password = edtPassword.text.toString().trim()
            val email = edtEmail.text.toString().trim()

            if (username.isEmpty() || password.isEmpty() || email.isEmpty()) {
                Toast.makeText(this, "請完整填寫所有欄位", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }

            // 根據後端新 Schema 建立註冊資料
            val regData = RegisterRequest(
                username = username,
                password = password,
                email = email,
                full_name = username
            )

            // 呼叫 API，回傳型態改為 GenericResponse (對應後端 status, message)
            apiService.register(regData).enqueue(object : Callback<GenericResponse> {
                override fun onResponse(call: Call<GenericResponse>, response: Response<GenericResponse>) {
                    if (response.isSuccessful) {
                        val body = response.body()
                        Log.d("RegisterActivity", "Success: ${body?.message}")

                        // --- 【邏輯變更：引導去收信】 ---
                        showVerificationDialog(email)

                    } else {
                        // 嘗試解析後端傳回的錯誤訊息 (例如：Username already exists)
                        val errorBody = response.errorBody()?.string()
                        Log.e("RegisterActivity", "Error: $errorBody")
                        Toast.makeText(this@RegisterActivity, "註冊失敗：帳號或 Email 已被使用", Toast.LENGTH_LONG).show()
                    }
                }

                override fun onFailure(call: Call<GenericResponse>, t: Throwable) {
                    Log.e("RegisterActivity", "Failure: ${t.message}")
                    Toast.makeText(this@RegisterActivity, "連線失敗，請確認後端已啟動", Toast.LENGTH_SHORT).show()
                }
            })
        }

        tvBackLogin.setOnClickListener {
            finish()
        }
    }

    // 顯示對話框，提醒使用者去驗證信箱
    private fun showVerificationDialog(email: String) {
        AlertDialog.Builder(this)
            .setTitle("註冊成功！")
            .setMessage("我們已發送驗證信至：$email\n請先前往信箱點擊驗證連結，再回來登入喔！")
            .setCancelable(false)
            .setPositiveButton("我知道了") { _, _ ->
                // 點擊後回到登入頁面
                finish()
            }
            .show()
    }
}