package com.example.plantdoctor

import android.content.Context
import android.content.res.ColorStateList
import android.graphics.Color
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

class RegisterActivity : AppCompatActivity() {

    // 🌟 1. 建立風聲延遲計時器與任務
    private val windHandler = Handler(Looper.getMainLooper())
    private val windRunnable = Runnable {
        SoundManager.startWind() // 當按住滿 0.5 秒，正式吹起風聲
    }

    private lateinit var registerRoot: ConstraintLayout

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_register)

        // --- 2. 綁定 UI 元件 ---
        registerRoot = findViewById(R.id.register_root_layout) // 🌟 最外層佈局
        val edtUsername = findViewById<EditText>(R.id.et_reg_username)
        val edtPassword = findViewById<EditText>(R.id.et_reg_password)
        val edtEmail = findViewById<EditText>(R.id.et_reg_gmail)
        val btnSubmit = findViewById<Button>(R.id.btn_register_submit)
        val tvBackLogin = findViewById<TextView>(R.id.tv_back_to_login)
        val tvRegisterTitle = findViewById<TextView>(R.id.tv_register_title)

        // 🌟 初始化音效管理器
        SoundManager.init(this)

        // 🌟 召喚大總管！將最外層背景、註冊按鈕、返回文字交給它處理
        ThemeManager.applyTheme(
            context = this,
            rootLayout = registerRoot,
            titles = listOf(tvBackLogin, tvRegisterTitle),
            mainButtons = listOf(btnSubmit)
        )

        val apiService = PlantApiService.create(null)

        btnSubmit.setOnClickListener {
            SoundManager.playBubblePop()

            val username = edtUsername.text.toString().trim()
            val password = edtPassword.text.toString().trim()
            val email = edtEmail.text.toString().trim()

            if (username.isEmpty() || password.isEmpty() || email.isEmpty()) {
                Toast.makeText(this, "請完整填寫所有欄位", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }

            val regData = RegisterRequest(
                username = username,
                password = password,
                email = email,
                full_name = username
            )

            apiService.register(regData).enqueue(object : Callback<GenericResponse> {
                override fun onResponse(call: Call<GenericResponse>, response: Response<GenericResponse>) {
                    if (response.isSuccessful) {
                        val body = response.body()
                        Log.d("RegisterActivity", "Success: ${body?.message}")

                        val sharedPref = getSharedPreferences("PlantDoctor", Context.MODE_PRIVATE)
                        with(sharedPref.edit()) {
                            putString("registered_email", email)
                            apply()
                        }

                        showVerificationDialog(email)

                    } else {
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
            SoundManager.playBubblePop()
            finish()
        }
    }

    override fun onResume() {
        super.onResume()
        // 🌟 每次回到註冊頁時，重新刷新主題色彩與啟動背景音樂
        if (::registerRoot.isInitialized) {
            val tvBackLogin = findViewById<TextView>(R.id.tv_back_to_login)
            val tvRegisterTitle = findViewById<TextView>(R.id.tv_register_title)
            val btnSubmit = findViewById<Button>(R.id.btn_register_submit)

            ThemeManager.applyTheme(
                context = this,
                rootLayout = registerRoot,
                titles = listOf(tvBackLogin, tvRegisterTitle),
                mainButtons = listOf(btnSubmit)
            )
        }
        SoundManager.startBGM()
    }

    /**
     * 🌟 核心關鍵突破：搶在 ScrollView 吃掉事件之前分發 Touch 事件！
     * 無論頁面是否有 ScrollView 滾動，按住畫面 0.5 秒依然會吹起風聲。
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

    // 顯示對話框，提醒使用者去驗證信箱（動態對齊當前主題色彩）
    private fun showVerificationDialog(email: String) {
        val sharedPref = getSharedPreferences("PlantDoctor", Context.MODE_PRIVATE)
        val currentTheme = sharedPref.getInt("THEME_COLOR_ID", 0)

        val textColorStr = if (currentTheme in 1..3) "#FFFFFF" else "#222222"
        val bgColorStr = when (currentTheme) {
            1 -> "#1A237E"
            2 -> "#3E2723"
            3 -> "#4A0033"
            else -> "#FFFFFF"
        }
        val textColor = Color.parseColor(textColorStr)
        val bgColor = Color.parseColor(bgColorStr)

        val dialogLayout = android.widget.LinearLayout(this).apply {
            orientation = android.widget.LinearLayout.VERTICAL
            setPadding(60, 50, 60, 40)
        }

        val tvTitle = TextView(this).apply {
            text = "註冊成功！"
            textSize = 20f
            typeface = android.graphics.Typeface.create(android.graphics.Typeface.DEFAULT, android.graphics.Typeface.BOLD)
            setTextColor(textColor)
            setPadding(0, 10, 0, 20)
        }

        val tvMessage = TextView(this).apply {
            text = "我們已發送驗證信至：\n$email\n\n請先前往信箱點擊驗證連結，再回來登入喔！"
            textSize = 16f
            setTextColor(textColor)
            setPadding(0, 0, 0, 20)
        }

        dialogLayout.addView(tvTitle)
        dialogLayout.addView(tvMessage)

        val alertDialog = AlertDialog.Builder(this)
            .setView(dialogLayout)
            .setCancelable(false)
            .setPositiveButton("我知道了") { _, _ ->
                SoundManager.playBubblePop()
                finish()
            }
            .create()

        alertDialog.show()

        alertDialog.window?.let { window ->
            val background = android.graphics.drawable.GradientDrawable().apply {
                setColor(bgColor)
                cornerRadius = 32f
            }
            window.setBackgroundDrawable(background)
            alertDialog.getButton(AlertDialog.BUTTON_POSITIVE)?.setTextColor(textColor)
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