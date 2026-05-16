package com.example.plantdoctor

import android.content.Context
import android.content.Intent
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
import retrofit2.Call
import retrofit2.Callback
import retrofit2.Response

class LoginActivity : AppCompatActivity() {

    // 🌟 1. 建立風聲延遲計時器與任務（放在 onCreate 外面）
    private val windHandler = Handler(Looper.getMainLooper())
    private val windRunnable = Runnable {
        SoundManager.startWind() // 當按住滿 0.5 秒，正式吹起風聲
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // --- 1. 免重複登入檢查 ---
        val sharedPref = getSharedPreferences("PlantDoctor", Context.MODE_PRIVATE)
        val isLoggedIn = sharedPref.getBoolean("is_logged_in", false)
        val savedToken = sharedPref.getString("token", null)

        if (isLoggedIn && savedToken != null) {
            goToHome()
            return
        }

        setContentView(R.layout.activity_login)

        // --- 2. 綁定 UI 元件 ---
        val etUsername = findViewById<EditText>(R.id.et_username)
        val etPassword = findViewById<EditText>(R.id.et_password)
        val btnLogin = findViewById<Button>(R.id.btn_login_submit)
        val tvRegister = findViewById<TextView>(R.id.tv_go_to_register)
        val tvForgotPassword = findViewById<TextView>(R.id.tv_forgot_password)

        // --- 3. 登入按鈕邏輯 ---
        btnLogin.setOnClickListener {
            // 🌟 核心修改：點擊登入按鈕播放泡泡聲
            SoundManager.playBubblePop()

            val username = etUsername.text.toString().trim()
            val password = etPassword.text.toString().trim()

            if (username.isEmpty() || password.isEmpty()) {
                Toast.makeText(this, "請輸入帳號和密碼", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }

            val apiService = PlantApiService.create(null)

            apiService.login(username, password).enqueue(object : Callback<LoginResponse> {
                override fun onResponse(call: Call<LoginResponse>, response: Response<LoginResponse>) {
                    if (response.isSuccessful) {
                        val body = response.body()
                        val token = body?.access_token
                        val email = body?.email

                        if (token != null) {
                            // 儲存登入狀態與資料
                            with(sharedPref.edit()) {
                                putBoolean("is_logged_in", true)
                                putString("token", token)
                                putString("username", username)
                                putString("email", email)
                                apply()
                            }
                            Toast.makeText(this@LoginActivity, "登入成功！", Toast.LENGTH_SHORT).show()
                            goToHome()
                        }
                    } else {
                        when (response.code()) {
                            403 -> showErrorDialog("登入失敗", "您的信箱尚未驗證，請先至信箱點擊驗證連結。")
                            400 -> Toast.makeText(this@LoginActivity, "帳號或密碼錯誤", Toast.LENGTH_SHORT).show()
                            else -> Toast.makeText(this@LoginActivity, "登入失敗，請稍後再試", Toast.LENGTH_SHORT).show()
                        }
                    }
                }

                override fun onFailure(call: Call<LoginResponse>, t: Throwable) {
                    Log.e("LoginActivity", "Network Error: ${t.message}")
                    Toast.makeText(this@LoginActivity, "連線失敗，請檢查網路或伺服器", Toast.LENGTH_SHORT).show()
                }
            })
        }

        // --- 4. 註冊跳轉 ---
        tvRegister.setOnClickListener {
            // 🌟 核心修改：點擊去註冊播放泡泡聲
            SoundManager.playBubblePop()
            startActivity(Intent(this, RegisterActivity::class.java))
        }

        // --- 5. 忘記密碼跳轉 ---
        tvForgotPassword.setOnClickListener {
            // 🌟 核心修改：點擊忘記密碼播放泡泡聲
            SoundManager.playBubblePop()
            showForgotPasswordDialog()
        }
    }

    private fun goToHome() {
        val intent = Intent(this, HomeActivity::class.java)
        startActivity(intent)
        finish()
    }

    private fun showForgotPasswordDialog() {
        val builder = AlertDialog.Builder(this)
        builder.setTitle("忘記密碼")
        builder.setMessage("請輸入您的註冊 Email，系統將寄送重設密碼連結：")

        val input = EditText(this)
        input.hint = "example@gmail.com"
        input.setPadding(50, 40, 50, 40)
        builder.setView(input)

        builder.setPositiveButton("送出") { _, _ ->
            // 🌟 核心修改：點擊忘記密碼彈窗的「送出」播放泡泡聲
            SoundManager.playBubblePop()
            val email = input.text.toString().trim()
            if (email.isNotEmpty() && android.util.Patterns.EMAIL_ADDRESS.matcher(email).matches()) {
                sendResetEmail(email)
            } else {
                Toast.makeText(this, "請輸入有效的 Email 地址", Toast.LENGTH_SHORT).show()
            }
        }
        builder.setNegativeButton("取消") { _, _ ->
            // 🌟 核心修改：點擊忘記密碼彈窗的「取消」播放泡泡聲
            SoundManager.playBubblePop()
        }
        builder.show()
    }

    private fun sendResetEmail(email: String) {
        val apiService = PlantApiService.create(null)
        val request = ForgotPasswordRequest(email)

        apiService.forgotPassword(request).enqueue(object : Callback<GenericResponse> {
            override fun onResponse(call: Call<GenericResponse>, response: Response<GenericResponse>) {
                if (response.isSuccessful) {
                    Toast.makeText(this@LoginActivity, "若 Email 正確，重設信件已寄出！", Toast.LENGTH_LONG).show()
                } else {
                    Toast.makeText(this@LoginActivity, "發送失敗，請稍後再試", Toast.LENGTH_SHORT).show()
                }
            }
            override fun onFailure(call: Call<GenericResponse>, t: Throwable) {
                Toast.makeText(this@LoginActivity, "網路連線失敗", Toast.LENGTH_SHORT).show()
            }
        })
    }

    private fun showErrorDialog(title: String, message: String) {
        AlertDialog.Builder(this)
            .setTitle(title)
            .setMessage(message)
            .setPositiveButton("確定") { _, _ ->
                // 🌟 核心修改：點擊錯誤彈窗的「確定」播放泡泡聲
                SoundManager.playBubblePop()
            }
            .show()
    }

    // 🌟 2. 核心修改：全螢幕長按雷達，判定長按 0.5 秒才吹風
    override fun onTouchEvent(event: MotionEvent?): Boolean {
        if (event != null) {
            when (event.action) {
                MotionEvent.ACTION_DOWN -> {
                    // 手指一碰到螢幕任意處：先設定一個 0.5 秒後的鬧鐘
                    windHandler.postDelayed(windRunnable, 500)
                }
                MotionEvent.ACTION_UP, MotionEvent.ACTION_CANCEL -> {
                    // 手指一離開或滑開螢幕：撤銷鬧鐘，停止風聲
                    windHandler.removeCallbacks(windRunnable)
                    SoundManager.stopWind()
                }
            }
        }
        return super.onTouchEvent(event)
    }

    // 🌟 3. 核心修改：離開畫面時，安全切斷風聲並復原計時器
    override fun onStop() {
        super.onStop()
        SoundManager.stopWind()
        windHandler.removeCallbacks(windRunnable)
    }

    // 🌟 4. 銷毀畫面時清空計時器，防止記憶體洩漏
    override fun onDestroy() {
        super.onDestroy()
        windHandler.removeCallbacksAndMessages(null)
    }
}