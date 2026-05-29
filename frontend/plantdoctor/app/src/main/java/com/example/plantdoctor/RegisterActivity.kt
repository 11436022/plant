package com.example.plantdoctor

import android.content.Context
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.view.MotionEvent
import android.util.Log
import android.widget.Button
import android.widget.EditText
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.constraintlayout.widget.ConstraintLayout // 🌟 新增
import retrofit2.Call
import retrofit2.Callback
import retrofit2.Response

class RegisterActivity : AppCompatActivity() {

    // 🌟 1. 建立風聲延遲計時器與任務（放在 onCreate 外面）
    private val windHandler = Handler(Looper.getMainLooper())
    private val windRunnable = Runnable {
        SoundManager.startWind() // 當按住滿 0.5 秒，正式吹起風聲
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_register)

        // --- 2. 綁定 UI 元件 ---
        val registerRoot = findViewById<ConstraintLayout>(R.id.register_root_layout) // 🌟 核心新增：最外層佈局
        val edtUsername = findViewById<EditText>(R.id.et_reg_username)
        val edtPassword = findViewById<EditText>(R.id.et_reg_password)
        val edtEmail = findViewById<EditText>(R.id.et_reg_gmail)
        val btnSubmit = findViewById<Button>(R.id.btn_register_submit)
        val tvBackLogin = findViewById<TextView>(R.id.tv_back_to_login)
        val tvRegisterTitle = findViewById<TextView>(R.id.tv_register_title)

        // 🌟 核心新增：召喚大總管！將最外層背景、註冊按鈕、返回文字交給它處理
        ThemeManager.applyTheme(
            context = this,
            rootLayout = registerRoot,
            titles = listOf(tvBackLogin,tvRegisterTitle), // 讓「返回登入」文字同步換成主題深色系字體
            mainButtons = listOf(btnSubmit) // 讓「註冊送出按鈕」同步對齊主題色
        )

        // 註冊時不需要 Token，所以傳 null 建立 API Service
        val apiService = PlantApiService.create(null)

        btnSubmit.setOnClickListener {
            // 點擊送出按鈕播放泡泡聲
            SoundManager.playBubblePop()

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

                        // 🌟 在 RegisterActivity 收到註冊成功回應的地方加入這段：
                        val sharedPref = getSharedPreferences("PlantDoctor", Context.MODE_PRIVATE)
                        with(sharedPref.edit()) {
                            putString("registered_email", email) // 👈 把剛註冊成功的 Email 存起來，鑰匙叫 "registered_email"
                            apply()
                        }

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
            // 點擊返回登入播放泡泡聲
            SoundManager.playBubblePop()
            finish()
        }
    } // onCreate 的結尾

    // 顯示對話框，提醒使用者去驗證信箱
    private fun showVerificationDialog(email: String) {
        AlertDialog.Builder(this)
            .setTitle("註冊成功！")
            .setMessage("我們已發送驗證信至：$email\n請先前往信箱點擊驗證連結，再回來登入喔！")
            .setCancelable(false)
            .setPositiveButton("我知道了") { _, _ ->
                // 點擊對話框按鈕時播放泡泡聲
                SoundManager.playBubblePop()
                // 點擊後回到登入頁面
                finish()
            }
            .show()
    }

    // 🌟 全螢幕長按雷達，判定長按 0.5 秒才吹風
    override fun onTouchEvent(event: MotionEvent?): Boolean {
        if (event != null) {
            when (event.action) {
                MotionEvent.ACTION_DOWN -> {
                    windHandler.postDelayed(windRunnable, 500)
                }
                MotionEvent.ACTION_UP, MotionEvent.ACTION_CANCEL -> {
                    windHandler.removeCallbacks(windRunnable)
                    SoundManager.stopWind()
                }
            }
        }
        return super.onTouchEvent(event)
    }

    override fun onStop() {
        super.onStop()
        SoundManager.stopWind()
        windHandler.removeCallbacks(windRunnable)
    }

    override fun onDestroy() {
        super.onDestroy()
        windHandler.removeCallbacksAndMessages(null)
    }
}