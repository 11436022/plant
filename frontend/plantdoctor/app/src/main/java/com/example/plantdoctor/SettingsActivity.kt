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
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.constraintlayout.widget.ConstraintLayout
import retrofit2.Call
import retrofit2.Callback
import retrofit2.Response

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
        val tvForgotPassword = findViewById<TextView>(R.id.tv_forgot_password)
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
        val themes = arrayOf("🌿 經典陽光綠", "🌌 深邃星空藍", "\uD83E\uDEB5 暖陽落日橙", "\uD83C\uDF38 微醺初戀粉")
        val sharedPref = getSharedPreferences("PlantDoctor", Context.MODE_PRIVATE)
        val currentTheme = sharedPref.getInt("THEME_COLOR_ID", 0)

        AlertDialog.Builder(this)
            .setTitle("選擇背景主題色彩")
            .setSingleChoiceItems(themes, currentTheme) { dialog, which ->
                SoundManager.playBubblePop()
                // 1. 儲存選擇的主題編號
                sharedPref.edit().putInt("THEME_COLOR_ID", which).apply()
                // 2. 即時更換當前頁面所有色彩
                applyThemeSettings(which)
                dialog.dismiss()
                Toast.makeText(this, "主題切換成功！", Toast.LENGTH_SHORT).show()
            }
            .setNegativeButton("取消") { dialog, _ ->
                SoundManager.playBubblePop()
                dialog.dismiss()
            }
            .show()
    }

    /**
     * 🌟 核心新增：負責全套 UI 主題色抽換的大總管
     */
    private fun applyThemeSettings(themeId: Int) {
        // 🌟 直接呼叫大總管，把設定頁的元件傳進去，打完收工！
        ThemeManager.applyTheme(
            context = this,
            rootLayout = rootLayout,
            titles = listOf(tvSettingsTitle, tvColorSelect),
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

        // 根據當前主題決定調音台滑桿的顏色
        val themeColorStr = when (currentTheme) {
            1 -> "#64B5F6" // 藍
            2 -> "#C2185B" // 粉
            3 -> "#7B1FA2" // 紫
            else -> "#2E7D32" // 綠
        }
        val themeColor = Color.parseColor(themeColorStr)

        val volStartApp = sharedPref.getInt("VOL_START_APP", 35)
        val volBgm = sharedPref.getInt("VOL_BGM", 70)
        val volBubble = sharedPref.getInt("VOL_BUBBLE", 70)
        val volWind = sharedPref.getInt("VOL_WIND", 70)

        val context = this
        val dialogLayout = LinearLayout(context).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(50, 40, 50, 40)
        }

        fun createVolumeRow(label: String, currentProgress: Int, onRelease: (Int) -> Unit): SeekBar {
            val tv = TextView(context).apply {
                text = "$label ($currentProgress%)"
                textSize = 16f
                setTextColor(themeColor) // 🌟 同步換色：對齊主題色
                setPadding(0, 20, 0, 10)
            }
            val seekBar = SeekBar(context).apply {
                max = 100
                progress = currentProgress
                thumbTintList = ColorStateList.valueOf(themeColor) // 🌟 同步換色：滑桿按鈕
                progressTintList = ColorStateList.valueOf(themeColor) // 🌟 同步換色：進度條
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

        AlertDialog.Builder(this)
            .setTitle("進階音量控制調音台")
            .setView(dialogLayout)
            .setPositiveButton("完成設定") { _, _ -> SoundManager.playBubblePop() }
            .show()
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