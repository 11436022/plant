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
import org.json.JSONObject
import retrofit2.Call
import retrofit2.Callback
import retrofit2.Response

class LoginActivity : AppCompatActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // 【功能 1：免重複登入檢查】
        // 在載入佈局前先檢查是否已經有登入紀錄
        val sharedPref = getSharedPreferences("PlantDoctor", Context.MODE_PRIVATE)
        val isLoggedIn = sharedPref.getBoolean("is_logged_in", false)

        if (isLoggedIn) {
            // 如果已經登入，直接跳轉到主頁
            val intent = Intent(this, HomeActivity::class.java)
            startActivity(intent)
            finish()
            return // 結束 onCreate，不執行後續佈局
        }

        setContentView(R.layout.activity_login)

        // 1. 綁定 UI
        val etUsername = findViewById<EditText>(R.id.et_username)
        val etPassword = findViewById<EditText>(R.id.et_password)
        val btnLogin = findViewById<Button>(R.id.btn_login_submit)
        val tvRegister = findViewById<TextView>(R.id.tv_go_to_register)

        // 2. 登入邏輯
        btnLogin.setOnClickListener {
            val username = etUsername.text.toString().trim()
            val password = etPassword.text.toString().trim()

            if (username.isEmpty() || password.isEmpty()) {
                Toast.makeText(this, "請輸入帳號和密碼", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }

            val apiService = PlantApiService.create()
            val loginData = LoginRequest(username, password)

            apiService.login(loginData).enqueue(object : Callback<ResponseBody> {
                override fun onResponse(call: Call<ResponseBody>, response: Response<ResponseBody>) {
                    if (response.isSuccessful) {
                        val responseBody = response.body()?.string()
                        val jsonObject = JSONObject(responseBody ?: "")

                        // 取得 Token 與其他用戶資訊
                        val token = jsonObject.optString("access_token")
                        // 假設後端登入成功會回傳 email，若無，我們暫時存入帳號
                        val email = jsonObject.optString("email") // 現在這行能抓到真正的 Email 了！

                        // 【功能 2：儲存登入狀態與個人資料】
                        with(sharedPref.edit()) {
                            putBoolean("is_logged_in", true)          // 記住已登入
                            putString("token", "Bearer $token")       // 存 Token
                            putString("username", username)           // 存帳號
                            putString("email", email)                 // 存 Email
                            apply()
                        }

                        Toast.makeText(this@LoginActivity, "登入成功！", Toast.LENGTH_SHORT).show()

                        val intent = Intent(this@LoginActivity, HomeActivity::class.java)
                        startActivity(intent)
                        finish()
                    } else {
                        val errorDetail = response.errorBody()?.string()
                        Log.e("LoginActivity", "Login Failed: $errorDetail")
                        Toast.makeText(this@LoginActivity, "登入失敗：帳號或密碼錯誤", Toast.LENGTH_SHORT).show()
                    }
                }

                override fun onFailure(call: Call<ResponseBody>, t: Throwable) {
                    Log.e("LoginActivity", "Network Error: ${t.message}")
                    Toast.makeText(this@LoginActivity, "連線失敗，請檢查後端是否開啟", Toast.LENGTH_SHORT).show()
                }
            })
        }

        tvRegister.setOnClickListener {
            val intent = Intent(this, RegisterActivity::class.java)
            startActivity(intent)
        }
    }
}