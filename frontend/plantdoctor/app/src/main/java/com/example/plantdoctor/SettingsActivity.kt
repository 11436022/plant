package com.example.plantdoctor

import android.content.Context
import android.content.Intent
import android.content.res.ColorStateList
import android.graphics.Color
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.view.MotionEvent
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.SeekBar
import android.widget.TextView
import android.widget.Toast
import android.util.Log
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.constraintlayout.widget.ConstraintLayout
import retrofit2.Call
import retrofit2.Callback
import retrofit2.Response
import android.view.View
import com.example.plantdoctor.R

class SettingsActivity : AppCompatActivity() {

    // 🌟 風聲延遲計時器與任務
    private val windHandler = Handler(Looper.getMainLooper())
    private val windRunnable = Runnable {
        SoundManager.startWind()
    }

    // 🌟 全域宣告需要動態換色的 UI 元件
    private lateinit var rootLayout: ConstraintLayout
    private lateinit var tvSettingsTitle: TextView
    private lateinit var tvColorSelect: TextView
    private lateinit var tvForgotPassword: TextView

    private lateinit var etUsername: EditText
    private lateinit var etGmail: EditText

    private lateinit var btnBack: android.widget.ImageButton
    private lateinit var btnVolumeMixer: android.widget.ImageButton
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_settings)

        // --- 1. 取得 SharedPreferences 資料 ---
        val sharedPref = getSharedPreferences("PlantDoctor", Context.MODE_PRIVATE)
        val savedUsername = sharedPref.getString("username", "尚未登錄")
        val savedEmail = sharedPref.getString("email", "尚未設定 Email")

        // --- 2. 綁定 UI ---
        rootLayout = findViewById(R.id.settings_root_layout)
        tvSettingsTitle = findViewById(R.id.tv_settings_title)
        tvColorSelect = findViewById(R.id.tv_color_select)
        tvForgotPassword = findViewById(R.id.tv_forgot_password)
        etUsername = findViewById(R.id.et_username)
        etGmail = findViewById(R.id.et_gmail)
        btnVolumeMixer = findViewById(R.id.btn_volume_mixer)
        btnBack = findViewById(R.id.btn_back_home)
        val btnLogout = findViewById<Button>(R.id.btn_logout)

        // --- 3. 從 API 取得最新使用者資料 ---
        fetchUserProfile()

        // 🌟 初始化音效管理器 (與 HomeActivity 對齊)
        SoundManager.init(this)

        // 🌟 核心新增：一開機就套用上次使用者選好的主題顏色
        val savedTheme = sharedPref.getInt("THEME_COLOR_ID", 0) // 預設 0 是經典綠
        applyThemeSettings(savedTheme)

        // --- 5. 點擊事件處理 ---
        btnBack.setOnClickListener {
            SoundManager.playBubblePop()
            finish()
        }

        tvForgotPassword.setOnClickListener {
            SoundManager.playBubblePop()
            showForgotPasswordDialog(savedEmail ?: "")
        }

        tvColorSelect.setOnClickListener {
            SoundManager.playBubblePop()
            showColorSelectDialog()
        }

        btnLogout.setOnClickListener {
            SoundManager.playBubblePop()
            with(sharedPref.edit()) {
                remove("token")
                remove("username")
                remove("email")
                apply()
            }
            Toast.makeText(this, "已成功登出", Toast.LENGTH_SHORT).show()

            val intent = Intent(this, LoginActivity::class.java)
            intent.flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
            startActivity(intent)
            finish()
        }
    }

    override fun onResume() {
        super.onResume()
        // 🌟 回到頁面時，強迫大總管重新載入最新主題背景與標題顏色，並重新播放背景音效
        applyThemeSettings(getSharedPreferences("PlantDoctor", Context.MODE_PRIVATE).getInt("THEME_COLOR_ID", 0))
        SoundManager.startBGM()
    }

    /**
     * 🌟 核心關鍵突破：搶在 ScrollView 吃掉事件之前分發 Touch 事件！
     * 無論頁面有沒有滾動條，按住畫面 0.5 秒依然會完美發出風聲。
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

    /**
     * 🌟 核心新增：顯示背景顏色選擇器彈窗
     */
    private fun showColorSelectDialog() {
        val themes = arrayOf("🌿 經典陽光綠", "🌌 清新大海藍", "\uD83E\uDEB5 暖陽落日橙", "\uD83C\uDF38 微醺初戀粉")
        val sharedPref = getSharedPreferences("PlantDoctor", Context.MODE_PRIVATE)
        val currentTheme = sharedPref.getInt("THEME_COLOR_ID", 0)

        // 1. 根據目前的主題，動態決定「底色」與「字體顏色」
        val bgColorStr = when (currentTheme) {
            1 -> "#1A237E" // 藍底
            2 -> "#3E2723" // 棕底
            3 -> "#4A0033" // 粉底
            else -> "#FFFFFF" // 綠色（預設白底）
        }
        val textColorStr = when (currentTheme) {
            1, 2, 3 -> "#FFFFFF" // 暗色系背景配純白字
            else -> "#222222" // 綠色主題白底配深灰色字
        }

        val bgColor = Color.parseColor(bgColorStr)
        val textColor = Color.parseColor(textColorStr)

        val context = this
        // 2. 自己建立最外層的大佈局
        val dialogLayout = LinearLayout(context).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(60, 50, 60, 40)
        }

        // 3. 自己建立大標題 (保證顏色絕對聽話)
        val tvDialogTitle = TextView(context).apply {
            text = "選擇背景主題色彩"
            textSize = 20f
            typeface = android.graphics.Typeface.create(android.graphics.Typeface.DEFAULT, android.graphics.Typeface.BOLD)
            setTextColor(textColor)
            setPadding(0, 10, 0, 30)
        }
        dialogLayout.addView(tvDialogTitle)

        // 4. 自己建立 RadioGroup 讓使用者單選
        val radioGroup = android.widget.RadioGroup(context).apply {
            orientation = LinearLayout.VERTICAL
        }

        // 5. 動態產生 4 個 RadioButton 項目，並強制上色！
        themes.forEachIndexed { index, themeName ->
            val radioButton = android.widget.RadioButton(context).apply {
                id = index
                text = themeName
                textSize = 16f
                setTextColor(textColor) // 🌟 強制選項文字顏色
                setPadding(20, 20, 0, 20)

                // 🌟 這裡連單選的小圓圈都一起換色！
                buttonTintList = ColorStateList.valueOf(textColor)

                // 勾選目前正在使用的主題
                isChecked = (index == currentTheme)
            }
            radioGroup.addView(radioButton)
        }
        dialogLayout.addView(radioGroup)

        // 6. 用這個 100% 自訂的佈局建立對話框
        val builder = AlertDialog.Builder(this)
            .setView(dialogLayout)
            .setPositiveButton("確定") { _, _ ->
                SoundManager.playBubblePop()
                val selectedId = radioGroup.checkedRadioButtonId
                if (selectedId != -1) {
                    // 儲存選擇的主題編號
                    sharedPref.edit().putInt("THEME_COLOR_ID", selectedId).apply()
                    // 即時更換當前頁面所有色彩
                    applyThemeSettings(selectedId)
                    Toast.makeText(this, "主題切換成功！", Toast.LENGTH_SHORT).show()
                }
            }
            .setNegativeButton("取消") { dialog, _ ->
                SoundManager.playBubblePop()
                dialog.dismiss()
            }

        val alertDialog = builder.create()
        alertDialog.show()

        // 7. 渲染最後的大底盤背景色與按鈕顏色
        alertDialog.window?.let { window ->
            val background = android.graphics.drawable.GradientDrawable().apply {
                setColor(bgColor)
                cornerRadius = 32f
            }
            window.setBackgroundDrawable(background)

            // 幫下方的「確定」與「取消」按鈕字體上色
            alertDialog.getButton(AlertDialog.BUTTON_POSITIVE)?.setTextColor(textColor)
            alertDialog.getButton(AlertDialog.BUTTON_NEGATIVE)?.setTextColor(textColor)
        }
    }

    /**
     * 🌟 負責全套 UI 主題色抽換的大總管
     */
    private fun applyThemeSettings(themeId: Int) {
        ThemeManager.applyTheme(
            context = this,
            rootLayout = rootLayout,
            titles = listOf(tvSettingsTitle, tvColorSelect, tvForgotPassword),
            imageButtons = listOf(btnBack, btnVolumeMixer)
        )
    }

    /**
     * 🌟 四軌音量控制調音台（同步動態對齊當前主題色）
     */
    private fun showVolumeMixerDialog() {
        val sharedPref = getSharedPreferences("PlantDoctor", Context.MODE_PRIVATE)
        val currentTheme = sharedPref.getInt("THEME_COLOR_ID", 0)

        val themeColorStr = when (currentTheme) {
            1 -> "#64B5F6" // 海洋藍
            2 -> "#FFCC80" // 暖陽橙 (棕)
            3 -> "#F48FB1" // 蜜桃粉
            else -> "#2E7D32" // 經典綠
        }
        val themeColor = Color.parseColor(themeColorStr)

        val dialogBgColorStr = when (currentTheme) {
            1 -> "#1A237E" // 深藍底
            2 -> "#3E2723" // 深可可底
            3 -> "#4A0033" // 深莓紅底
            else -> "#FFFFFF" // 清爽白底
        }
        val mainTitleColor = when (currentTheme) {
            1, 2, 3 -> Color.WHITE
            else -> Color.parseColor("#2E7D32")
        }

        val context = this
        val dialogLayout = LinearLayout(context).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(60, 50, 60, 50)
        }

        val tvDialogTitle = TextView(context).apply {
            text = "進階音量控制調音台"
            textSize = 20f
            typeface = android.graphics.Typeface.create(android.graphics.Typeface.DEFAULT, android.graphics.Typeface.BOLD)
            setTextColor(mainTitleColor)
            setPadding(0, 10, 0, 30)
        }
        dialogLayout.addView(tvDialogTitle)

        fun createVolumeRow(label: String, currentProgress: Int, onRelease: (Int) -> Unit): SeekBar {
            val rowTextColor = when (currentTheme) {
                1, 2, 3 -> Color.WHITE
                else -> themeColor
            }

            val tv = TextView(context).apply {
                text = "$label ($currentProgress%)"
                textSize = 16f
                setTextColor(rowTextColor)
                setPadding(0, 20, 0, 10)
            }
            val seekBar = SeekBar(context).apply {
                max = 100
                progress = currentProgress
                thumbTintList = ColorStateList.valueOf(themeColor)
                progressTintList = ColorStateList.valueOf(themeColor)
            }

            seekBar.setOnSeekBarChangeListener(object : SeekBar.OnSeekBarChangeListener {
                override fun onProgressChanged(sb: SeekBar?, prog: Int, fromUser: Boolean) {
                    tv.text = "$label ($prog%)"
                }
                override fun onStartTrackingTouch(sb: SeekBar?) {}
                override fun onStopTrackingTouch(sb: SeekBar?) {
                    onRelease(seekBar.progress)
                }
            })

            dialogLayout.addView(tv)
            dialogLayout.addView(seekBar)
            return seekBar
        }

        val volStartApp = sharedPref.getInt("VOL_START_APP", 35)
        val volBgm = sharedPref.getInt("VOL_BGM", 70)
        val volBubble = sharedPref.getInt("VOL_BUBBLE", 70)
        val volWind = sharedPref.getInt("VOL_WIND", 70)

        createVolumeRow("1. 開 App 音效音量", volStartApp) { progress ->
            val volFloat = progress / 100f
            sharedPref.edit().putInt("VOL_START_APP", progress).apply()
            SoundManager.setStartAppVolume(volFloat)
        }

        createVolumeRow("2. 背景音樂音量", volBgm) { progress ->
            val volFloat = progress / 100f
            sharedPref.edit().putInt("VOL_BGM", progress).apply()
            SoundManager.setBgmVolume(volFloat)
        }

        createVolumeRow("3. 泡泡聲特效音量", volBubble) { progress ->
            val volFloat = progress / 100f
            sharedPref.edit().putInt("VOL_BUBBLE", progress).apply()
            SoundManager.setBubbleVolume(volFloat)
            SoundManager.playBubblePop()
        }

        createVolumeRow("4. 雷達風聲特效音量", volWind) { progress ->
            val volFloat = progress / 100f
            sharedPref.edit().putInt("VOL_WIND", progress).apply()
            SoundManager.setWindVolume(volFloat)
            SoundManager.startWind()
            Handler(Looper.getMainLooper()).postDelayed({ SoundManager.stopWind() }, 600)
        }

        val builder = AlertDialog.Builder(this)
            .setView(dialogLayout)
            .setPositiveButton("完成設定") { _, _ -> SoundManager.playBubblePop() }

        val alertDialog = builder.create()
        alertDialog.show()

        alertDialog.window?.let { window ->
            val background = android.graphics.drawable.GradientDrawable().apply {
                setColor(Color.parseColor(dialogBgColorStr))
                cornerRadius = 32f
            }
            window.setBackgroundDrawable(background)
            alertDialog.getButton(AlertDialog.BUTTON_POSITIVE)?.setTextColor(mainTitleColor)
        }
    }

    /**
     * 顯示忘記密碼彈窗
     */
    private fun showForgotPasswordDialog(currentEmail: String) {
        val sharedPref = getSharedPreferences("PlantDoctor", MODE_PRIVATE)
        val currentTheme = sharedPref.getInt("THEME_COLOR_ID", 0)

        val bgColorStr = when (currentTheme) {
            1 -> "#1A237E"
            2 -> "#3E2723"
            3 -> "#4A0033"
            else -> "#FFFFFF"
        }

        val titleColor = when (currentTheme) {
            1, 2, 3 -> Color.WHITE
            else -> Color.parseColor("#2E7D32")
        }

        val textColor = when (currentTheme) {
            1, 2, 3 -> Color.WHITE
            else -> Color.parseColor("#333333")
        }

        val themeMainColorStr = when (currentTheme) {
            1 -> "#64B5F6"
            2 -> "#FFCC80"
            3 -> "#F48FB1"
            else -> "#2E7D32"
        }
        val themeMainColor = Color.parseColor(themeMainColorStr)

        val context = this
        val dialogLayout = LinearLayout(context).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(60, 50, 60, 40)
        }

        val tvTitle = TextView(context).apply {
            text = "重設密碼"
            textSize = 20f
            typeface = android.graphics.Typeface.create(android.graphics.Typeface.DEFAULT, android.graphics.Typeface.BOLD)
            setTextColor(titleColor)
            setPadding(0, 10, 0, 10)
        }
        dialogLayout.addView(tvTitle)

        val tvMsg = TextView(context).apply {
            text = "系統將寄送重設連結至您的 Email："
            textSize = 14f
            setTextColor(textColor)
            setPadding(0, 0, 0, 20)
        }
        dialogLayout.addView(tvMsg)

        val input = EditText(context).apply {
            hint = "請輸入 Email"
            setText(currentEmail)
            setHintTextColor(Color.GRAY)
            setTextColor(textColor)
            background = android.graphics.drawable.GradientDrawable().apply {
                setColor(Color.parseColor("#22FFFFFF"))
                setStroke(2, themeMainColor)
                cornerRadius = 16f
            }
            setPadding(30, 20, 30, 20)
        }
        dialogLayout.addView(input)

        val builder = AlertDialog.Builder(this)
            .setView(dialogLayout)
            .setPositiveButton("送出") { _, _ ->
                SoundManager.playBubblePop()
                val email = input.text.toString().trim()
                if (email.isNotEmpty()) {
                    sendResetEmail(email)
                } else {
                    Toast.makeText(this, "Email 不能為空", Toast.LENGTH_SHORT).show()
                }
            }
            .setNegativeButton("取消") { _, _ ->
                SoundManager.playBubblePop()
            }

        val alertDialog = builder.create()
        alertDialog.show()

        alertDialog.window?.let { window ->
            val background = android.graphics.drawable.GradientDrawable().apply {
                setColor(Color.parseColor(bgColorStr))
                cornerRadius = 32f
            }
            window.setBackgroundDrawable(background)
            alertDialog.getButton(AlertDialog.BUTTON_POSITIVE)?.setTextColor(titleColor)
            alertDialog.getButton(AlertDialog.BUTTON_NEGATIVE)?.setTextColor(titleColor)
        }
    }

    /**
     * 🌟 核心新增：從後端 API 取得最新的使用者資料並更新 UI
     */
    private fun fetchUserProfile() {
        val sharedPref = getSharedPreferences("PlantDoctor", Context.MODE_PRIVATE)
        val token = sharedPref.getString("token", null)

        

        // 先用 SharedPreferences 的快取資料填充，避免 API 回來前畫面空白
        etUsername.setText(sharedPref.getString("username", "尚未登錄"))
        etGmail.setText(sharedPref.getString("email", "尚未設定 Email"))

        if (token == null) {
            return // 沒有 token，不需執行 API 呼叫
        }

        val apiService = PlantApiService.create(token)
        apiService.getUserProfile().enqueue(object : Callback<UserProfileResponse> {
            override fun onResponse(call: Call<UserProfileResponse>, response: Response<UserProfileResponse>) {
                if (response.isSuccessful) {
                    val userProfile = response.body()?.data
                    if (userProfile != null) {
                        etUsername.setText(userProfile.username)
                        etGmail.setText(userProfile.email)

                        // 更新 SharedPreferences 快取
                        with(sharedPref.edit()) {
                            putString("username", userProfile.username)
                            putString("email", userProfile.email)
                            apply()
                        }
                    }
                } else {
                    Toast.makeText(this@SettingsActivity, "無法獲取最新使用者資料", Toast.LENGTH_SHORT).show()
                }
            }

            override fun onFailure(call: Call<UserProfileResponse>, t: Throwable) {
                Toast.makeText(this@SettingsActivity, "網路連線失敗", Toast.LENGTH_SHORT).show()
            }
        })
    }

    /**
     * 呼叫 API 發送重設郵件
     */
    private fun sendResetEmail(email: String) {
        val apiService = PlantApiService.create(null)
        val request = ForgotPasswordRequest(email)

        apiService.forgotPassword(request).enqueue(object : Callback<GenericResponse> {
            override fun onResponse(call: Call<GenericResponse>, response: Response<GenericResponse>) {
                Log.d("SettingsActivity", "API Response: ${response.body().toString()}")

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