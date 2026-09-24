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
import androidx.constraintlayout.widget.ConstraintLayout
import retrofit2.Call
import retrofit2.Callback
import retrofit2.Response

class LoginActivity : AppCompatActivity() {

    // 🌟 1. 建立風聲延遲計時器與任務
    private val windHandler = Handler(Looper.getMainLooper())
    private val windRunnable = Runnable {
        SoundManager.startWind() // 當按住滿 0.5 秒，正式吹起風聲
    }

    private lateinit var loginRoot: ConstraintLayout

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
        loginRoot = findViewById(R.id.login_root_layout) // 🌟 最外層佈局
        val etUsername = findViewById<EditText>(R.id.et_username)
        val etPassword = findViewById<EditText>(R.id.et_password)
        val btnLogin = findViewById<Button>(R.id.btn_login_submit)
        val tvRegister = findViewById<TextView>(R.id.tv_go_to_register)
        val tvForgotPassword = findViewById<TextView>(R.id.tv_forgot_password)
        val tvLoginTitle = findViewById<TextView>(R.id.tv_login_title)

        // 🌟 初始化音效管理器
        SoundManager.init(this)

        // 🌟 召喚大總管！將最外層背景、按鈕、可點擊文字通通交給它換色
        ThemeManager.applyTheme(
            context = this,
            rootLayout = loginRoot,
            titles = listOf(tvRegister, tvForgotPassword, tvLoginTitle),
            mainButtons = listOf(btnLogin)
        )

        // --- 3. 登入按鈕邏輯 ---
        btnLogin.setOnClickListener {
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
                            403 -> {
                                val savedEmail = sharedPref.getString("registered_email", "") ?: ""
                                showErrorDialog("驗證提示", "您的信箱尚未驗證，請先至信箱點擊驗證連結。", savedEmail)
                            }
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
            SoundManager.playBubblePop()
            startActivity(Intent(this, RegisterActivity::class.java))
        }

        // --- 5. 忘記密碼跳轉 ---
        tvForgotPassword.setOnClickListener {
            SoundManager.playBubblePop()
            showForgotPasswordDialog()
        }
    }

    override fun onResume() {
        super.onResume()
        // 🌟 每次回到登入頁時，重新刷新主題色彩與啟動背景音樂
        if (::loginRoot.isInitialized) {
            val tvRegister = findViewById<TextView>(R.id.tv_go_to_register)
            val tvForgotPassword = findViewById<TextView>(R.id.tv_forgot_password)
            val tvLoginTitle = findViewById<TextView>(R.id.tv_login_title)
            val btnLogin = findViewById<Button>(R.id.btn_login_submit)

            ThemeManager.applyTheme(
                context = this,
                rootLayout = loginRoot,
                titles = listOf(tvRegister, tvForgotPassword, tvLoginTitle),
                mainButtons = listOf(btnLogin)
            )
        }
        SoundManager.startBGM()
    }

    /**
     * 🌟 核心關鍵突破：搶在 ScrollView 吃掉事件之前分發 Touch 事件！
     * 無論頁面是否有 NestedScrollView 滾動，按住畫面 0.5 秒依然會吹起風聲。
     */
    override fun dispatchTouchEvent(ev: MotionEvent?): Boolean {
        if (ev != null) {
            when (ev.action) {
                MotionEvent.ACTION_DOWN -> {
                    windHandler.postDelayed(windRunnable, 500)
                }
                MotionEvent.ACTION_UP, MotionEvent.ACTION_CANCEL -> {
                    windHandler.removeCallbacks(windRunnable)
                    SoundManager.stopWind()
                }
            }
        }
        return super.dispatchTouchEvent(ev)
    }

    private fun sendVerificationEmail(email: String) {
        val apiService = PlantApiService.create(null)
        val request = EmailVerificationRequest(email)

        apiService.requestEmailVerification(request).enqueue(object : Callback<GenericResponse> {
            override fun onResponse(call: Call<GenericResponse>, response: Response<GenericResponse>) {
                Toast.makeText(this@LoginActivity, "若 Email 正確且未驗證，驗證信已補寄完成！", Toast.LENGTH_LONG).show()
            }

            override fun onFailure(call: Call<GenericResponse>, t: Throwable) {
                Toast.makeText(this@LoginActivity, "網路連線失敗，請稍後再試", Toast.LENGTH_SHORT).show()
            }
        })
    }

    private fun goToHome() {
        val intent = Intent(this, HomeActivity::class.java)
        startActivity(intent)
        finish()
    }

    private fun showForgotPasswordDialog() {
        val sharedPref = getSharedPreferences("PlantDoctor", MODE_PRIVATE)
        val currentTheme = sharedPref.getInt("THEME_COLOR_ID", 0)

        val bgColorStr = when (currentTheme) {
            1 -> "#1A237E"
            2 -> "#3E2723"
            3 -> "#4A0033"
            else -> "#FFFFFF"
        }

        val titleColor = when (currentTheme) {
            1, 2, 3 -> android.graphics.Color.WHITE
            else -> android.graphics.Color.parseColor("#2E7D32")
        }

        val textColor = when (currentTheme) {
            1, 2, 3 -> android.graphics.Color.WHITE
            else -> android.graphics.Color.parseColor("#333333")
        }

        val themeMainColorStr = when (currentTheme) {
            1 -> "#64B5F6"
            2 -> "#FFCC80"
            3 -> "#F48FB1"
            else -> "#2E7D32"
        }
        val themeMainColor = android.graphics.Color.parseColor(themeMainColorStr)

        val context = this
        val dialogLayout = android.widget.LinearLayout(context).apply {
            orientation = android.widget.LinearLayout.VERTICAL
            setPadding(60, 50, 60, 40)
        }

        val tvTitle = android.widget.TextView(context).apply {
            text = "忘記密碼"
            textSize = 20f
            typeface = android.graphics.Typeface.create(android.graphics.Typeface.DEFAULT, android.graphics.Typeface.BOLD)
            setTextColor(titleColor)
            setPadding(0, 10, 0, 10)
        }
        dialogLayout.addView(tvTitle)

        val tvMsg = android.widget.TextView(context).apply {
            text = "請輸入您的註冊 Email，系統將寄送重設密碼連結："
            textSize = 14f
            setTextColor(textColor)
            setPadding(0, 0, 0, 20)
        }
        dialogLayout.addView(tvMsg)

        val input = android.widget.EditText(context).apply {
            hint = "example@gmail.com"
            setHintTextColor(android.graphics.Color.GRAY)
            setTextColor(textColor)
            background = android.graphics.drawable.GradientDrawable().apply {
                setColor(android.graphics.Color.parseColor("#22FFFFFF"))
                setStroke(2, themeMainColor)
                cornerRadius = 16f
            }
            setPadding(30, 20, 30, 20)
        }
        dialogLayout.addView(input)

        val builder = androidx.appcompat.app.AlertDialog.Builder(this)
            .setView(dialogLayout)
            .setPositiveButton("送出") { _, _ ->
                SoundManager.playBubblePop()
                val email = input.text.toString().trim()
                if (email.isNotEmpty() && android.util.Patterns.EMAIL_ADDRESS.matcher(email).matches()) {
                    sendResetEmail(email)
                } else {
                    Toast.makeText(this, "請輸入有效的 Email 地址", Toast.LENGTH_SHORT).show()
                }
            }
            .setNegativeButton("取消") { _, _ ->
                SoundManager.playBubblePop()
            }

        val alertDialog = builder.create()
        alertDialog.show()

        alertDialog.window?.let { window ->
            val background = android.graphics.drawable.GradientDrawable().apply {
                setColor(android.graphics.Color.parseColor(bgColorStr))
                cornerRadius = 32f
            }
            window.setBackgroundDrawable(background)
            alertDialog.getButton(androidx.appcompat.app.AlertDialog.BUTTON_POSITIVE)?.setTextColor(titleColor)
            alertDialog.getButton(androidx.appcompat.app.AlertDialog.BUTTON_NEGATIVE)?.setTextColor(titleColor)
        }
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

    private fun showErrorDialog(title: String, message: String, defaultEmail: String) {
        val sharedPref = getSharedPreferences("PlantDoctor", Context.MODE_PRIVATE)
        val currentTheme = sharedPref.getInt("THEME_COLOR_ID", 0)

        val textColorStr = if (currentTheme in 1..3) "#FFFFFF" else "#222222"
        val bgColorStr = when (currentTheme) {
            1 -> "#1A237E"
            2 -> "#3E2723"
            3 -> "#4A0033"
            else -> "#FFFFFF"
        }
        val textColor = android.graphics.Color.parseColor(textColorStr)
        val bgColor = android.graphics.Color.parseColor(bgColorStr)

        val context = this
        val dialogLayout = android.widget.LinearLayout(context).apply {
            orientation = android.widget.LinearLayout.VERTICAL
            setPadding(60, 50, 60, 40)
        }

        val tvTitle = android.widget.TextView(context).apply {
            text = title
            textSize = 20f
            typeface = android.graphics.Typeface.create(android.graphics.Typeface.DEFAULT, android.graphics.Typeface.BOLD)
            setTextColor(textColor)
            setPadding(0, 10, 0, 20)
        }

        val tvMessage = android.widget.TextView(context).apply {
            text = message
            textSize = 16f
            setTextColor(textColor)
            setPadding(0, 10, 0, 30)
        }

        dialogLayout.addView(tvTitle)
        dialogLayout.addView(tvMessage)

        val isEmailValid = defaultEmail.isNotEmpty() && android.util.Patterns.EMAIL_ADDRESS.matcher(defaultEmail).matches()

        val etEmailInput = android.widget.EditText(context).apply {
            hint = "請輸入您的註冊 Email"
            setTextColor(textColor)
            setHintTextColor(android.graphics.Color.GRAY)
            visibility = android.view.View.VISIBLE

            if (isEmailValid) {
                setText(defaultEmail)
            }
        }
        dialogLayout.addView(etEmailInput)

        val builder = AlertDialog.Builder(this)
            .setView(dialogLayout)
            .setPositiveButton("補寄驗證信") { _, _ ->
                SoundManager.playBubblePop()

                val finalEmail = etEmailInput.text.toString().trim()

                if (finalEmail.isNotEmpty() && android.util.Patterns.EMAIL_ADDRESS.matcher(finalEmail).matches()) {
                    sendVerificationEmail(finalEmail)
                } else {
                    Toast.makeText(context, "請輸入正確的 Email 格式", Toast.LENGTH_SHORT).show()
                }
            }
            .setNegativeButton("知道了") { dialog, _ ->
                SoundManager.playBubblePop()
                dialog.dismiss()
            }

        val alertDialog = builder.create()
        alertDialog.show()

        alertDialog.window?.let { window ->
            val background = android.graphics.drawable.GradientDrawable().apply {
                setColor(bgColor)
                cornerRadius = 32f
            }
            window.setBackgroundDrawable(background)
            alertDialog.getButton(AlertDialog.BUTTON_POSITIVE)?.setTextColor(textColor)
            alertDialog.getButton(AlertDialog.BUTTON_NEGATIVE)?.setTextColor(textColor)
        }
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