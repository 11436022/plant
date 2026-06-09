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
    private lateinit var btnBack: android.widget.ImageButton
    private lateinit var btnVolumeMixer: android.widget.ImageButton

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_settings)

        // --- 1. 取得 SharedPreferences 資料 ---
        val sharedPref = getSharedPreferences("PlantDoctor", Context.MODE_PRIVATE)
        val savedUsername = sharedPref.getString("username", "尚未登錄")
        val savedEmail = sharedPref.getString("email", "尚未設定 Email")

        // --- 2. 綁定 UI 並顯示資料 ---
        rootLayout = findViewById(R.id.settings_root_layout)
        tvSettingsTitle = findViewById(R.id.tv_settings_title)
        tvColorSelect = findViewById(R.id.tv_color_select)
        btnBack = findViewById(R.id.btn_back_home)
        btnVolumeMixer = findViewById(R.id.btn_volume_mixer)


        val etUsername = findViewById<EditText>(R.id.et_username)
        val etGmail = findViewById<EditText>(R.id.et_gmail)
        tvForgotPassword = findViewById(R.id.tv_forgot_password)
        val btnLogout = findViewById<Button>(R.id.btn_logout)

        etUsername.setText(savedUsername)
        etGmail.setText(savedEmail)

        // 🌟 核心新增：一開機就套用上次使用者選好的主題顏色
        val savedTheme = sharedPref.getInt("THEME_COLOR_ID", 0) // 預設 0 是經典綠
        applyThemeSettings(savedTheme)

        // --- 3. 點擊事件處理 ---

        // 點擊「獨立的喇叭按鈕」彈出四軌音量調音台
        btnVolumeMixer.setOnClickListener {
            SoundManager.playBubblePop()
            showVolumeMixerDialog()
        }

        // 返回上一頁
        btnBack.setOnClickListener {
            SoundManager.playBubblePop()
            finish()
        }

        // 忘記密碼 / 更改密碼
        tvForgotPassword.setOnClickListener {
            SoundManager.playBubblePop()
            showForgotPasswordDialog(savedEmail ?: "")
        }

        // 🌟 核心修改：點擊背景顏色選擇，彈出高對比選單
        tvColorSelect.setOnClickListener {
            SoundManager.playBubblePop()
            showColorSelectDialog()
        }

        // --- 4. 登出按鈕邏輯 ---
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

        // 6. 用這個 100% 自訂的佈局建立對話框，不使用原生 setTitle 和 setSingleChoiceItems 了！
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
     * 🌟 核心新增：負責全套 UI 主題色抽換的大總管
     */
    private fun applyThemeSettings(themeId: Int) {
        // 🌟 直接呼叫大總管，把設定頁的元件傳進去，打完收工！
        ThemeManager.applyTheme(
            context = this,
            rootLayout = rootLayout,
            titles = listOf(tvSettingsTitle, tvColorSelect,tvForgotPassword),
            imageButtons = listOf(btnBack, btnVolumeMixer)
            // 💡 登出按鈕和照片按鈕因為你想維持特殊色（紅色/橘黃），這裡就故意不傳進去，它們就不會被動到！
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

        // 根據主題決定對話框的底色與最上方大標題文字顏色
        val dialogBgColorStr = when (currentTheme) {
            1 -> "#1A237E" // 深藍底
            2 -> "#3E2723" // 深可可底
            3 -> "#4A0033" // 深莓紅底
            else -> "#FFFFFF" // 清爽白底
        }
        val mainTitleColor = when (currentTheme) {
            1, 2, 3 -> Color.WHITE // 暗色系背景時，大標題用白色才突兀、好看
            else -> Color.parseColor("#2E7D32") // 綠色主題白底時，大標題用深綠色
        }

        val context = this
        val dialogLayout = LinearLayout(context).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(60, 50, 60, 50) // 稍微加寬間距，排版更美
        }

        // 🌟 修正點：直接把「大標題」自己用 TextView 刻出來並塞進佈局最上方！100% 聽話不受系統劫持
        val tvDialogTitle = TextView(context).apply {
            text = "進階音量控制調音台"
            textSize = 20f
            typeface = android.graphics.Typeface.create(android.graphics.Typeface.DEFAULT, android.graphics.Typeface.BOLD)
            setTextColor(mainTitleColor) // 🌟 精準控制大標題顏色！
            setPadding(0, 10, 0, 30)
        }
        dialogLayout.addView(tvDialogTitle)

        fun createVolumeRow(label: String, currentProgress: Int, onRelease: (Int) -> Unit): SeekBar {
            // 這裡的文字顏色，如果是暗色底就給白色，白底就給主題色，確保字字清晰
            val rowTextColor = when (currentTheme) {
                1, 2, 3 -> Color.WHITE
                else -> themeColor
            }

            val tv = TextView(context).apply {
                text = "$label ($currentProgress%)"
                textSize = 16f
                setTextColor(rowTextColor) // 同步換色：對齊內部項目字體色
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

        // 🌟 修正點：在這裡不要呼叫 .setTitle() 了，因為上面已經自己加了 tvDialogTitle
        val builder = AlertDialog.Builder(this)
            .setView(dialogLayout)
            .setPositiveButton("完成設定") { _, _ -> SoundManager.playBubblePop() }

        val alertDialog = builder.create()
        alertDialog.show()

        alertDialog.window?.let { window ->
            // 建立帶圓角的純色背景，完全覆蓋掉原本系統的灰色背景
            val background = android.graphics.drawable.GradientDrawable().apply {
                setColor(Color.parseColor(dialogBgColorStr))
                cornerRadius = 32f
            }
            window.setBackgroundDrawable(background)

            // 順手把右下角「完成設定」按鈕文字也改成對應的主題色
            alertDialog.getButton(AlertDialog.BUTTON_POSITIVE)?.setTextColor(mainTitleColor)
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
        input.setText(currentEmail)
        input.setPadding(50, 40, 50, 40)
        builder.setView(input)

        builder.setPositiveButton("送出") { _, _ ->
            SoundManager.playBubblePop()
            val email = input.text.toString().trim()
            if (email.isNotEmpty()) {
                sendResetEmail(email)
            } else {
                Toast.makeText(this, "Email 不能為空", Toast.LENGTH_SHORT).show()
            }
        }
        builder.setNegativeButton("取消") { _, _ ->
            SoundManager.playBubblePop()
        }
        builder.show()
    }

    /**
     * 呼叫 API 發送重設郵件
     */
    private fun sendResetEmail(email: String) {
        val apiService = PlantApiService.create(null)
        val request = ForgotPasswordRequest(email)

        apiService.forgotPassword(request).enqueue(object : Callback<GenericResponse> {
            override fun onResponse(call: Call<GenericResponse>, response: Response<GenericResponse>) {
                // [DEBUG] 將從後端收到的原始回應印出，方便在 Logcat 中查看
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