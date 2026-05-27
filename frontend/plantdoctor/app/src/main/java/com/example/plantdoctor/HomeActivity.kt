package com.example.plantdoctor

import android.content.Intent
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.view.MotionEvent
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import androidx.cardview.widget.CardView
import androidx.constraintlayout.widget.ConstraintLayout
import com.getkeepsafe.taptargetview.TapTarget
import com.getkeepsafe.taptargetview.TapTargetSequence

class HomeActivity : AppCompatActivity() {

    private val windHandler = Handler(Looper.getMainLooper())
    private val windRunnable = Runnable {
        SoundManager.startWind()
    }

    private lateinit var homeRoot: ConstraintLayout
    private lateinit var cardDiagnose: CardView
    private lateinit var cardHistory: CardView
    private lateinit var cardSettings: CardView
    private lateinit var tvhomeTitle: TextView // 🌟 提升為全域變數，方便 onResume 存取

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        // 🌟 移除剛才誤加的 IntroActivity 攔截，完全改回你原本的設計！
        setContentView(R.layout.activity_home)

        // 1. 綁定元件
        homeRoot = findViewById(R.id.home_root_layout)
        cardDiagnose = findViewById(R.id.card_diagnose)
        cardHistory = findViewById(R.id.card_history)
        cardSettings = findViewById(R.id.card_settings)
        tvhomeTitle = findViewById(R.id.tv_home_title)

        // 3. 初始化音效管理器
        SoundManager.init(this)

        // 4. 按鈕點擊事件
        cardDiagnose.setOnClickListener {
            SoundManager.playBubblePop()
            val intent = Intent(this, UploadActivity::class.java)
            startActivity(intent)
        }

        cardHistory.setOnClickListener {
            SoundManager.playBubblePop()
            val intent = Intent(this, HistoryListActivity::class.java)
            startActivity(intent)
        }

        cardSettings.setOnClickListener {
            SoundManager.playBubblePop()
            val intent = Intent(this, SettingsActivity::class.java)
            startActivity(intent)
        }

        // 🌟 檢查是否需要顯示主頁新手指引
        val sharedPref = getSharedPreferences("PlantDoctor", MODE_PRIVATE)
        val isFirstTime = sharedPref.getBoolean("IS_FIRST_TIME_HOME", true)

        if (isFirstTime) {
            showTutorial()
        }
    }

    override fun onResume() {
        super.onResume()

        // 🌟 核心新增：每次回到主頁時，強迫大總管重新載入最新主題背景與標題顏色！
        ThemeManager.applyTheme(this, homeRoot, titles = listOf(tvhomeTitle))

        // 重新載入音效設定 (假設 SoundManager 內部會處理)
        SoundManager.startBGM()
    }

    private fun showTutorial() {
        val targetColorRes = android.R.color.holo_green_dark
        val sharedPref = getSharedPreferences("PlantDoctor", MODE_PRIVATE)

        // 🌟 宣告專屬的定時跳轉大總管與各步驟的控制變數
        val guideHandler = Handler(Looper.getMainLooper())
        var targetView1: com.getkeepsafe.taptargetview.TapTargetView? = null
        var targetView2: com.getkeepsafe.taptargetview.TapTargetView? = null
        var targetView3: com.getkeepsafe.taptargetview.TapTargetView? = null

        // 🌟 狀態防禦鎖：記錄當前真正執行的步驟，防止連點與重複觸發
        var currentStep = 1

        // 🌟 定義 3 秒時間到的自動跳轉指令 (Runnable)
        val jumpToStep2Runnable = Runnable { targetView1?.dismiss(true) }
        val jumpToStep3Runnable = Runnable { targetView2?.dismiss(true) }
        val finishGuideRunnable = Runnable { targetView3?.dismiss(true) }

        // 3️⃣ 第三步：設定
        val startStep3 = {
            if (currentStep == 3) { // 確保只會執行一次
                SoundManager.playBubblePop()
                targetView3 = com.getkeepsafe.taptargetview.TapTargetView.showFor(this,
                    com.getkeepsafe.taptargetview.TapTarget.forView(cardSettings, "設定", "調整應用程式設定")
                        .outerCircleColor(targetColorRes)
                        .targetCircleColor(android.R.color.white)
                        .titleTextColor(android.R.color.white)
                        .descriptionTextColor(android.R.color.white)
                        .cancelable(false).tintTarget(false).transparentTarget(true).drawShadow(true),
                    object : com.getkeepsafe.taptargetview.TapTargetView.Listener() {
                        override fun onTargetClick(view: com.getkeepsafe.taptargetview.TapTargetView?) {
                            super.onTargetClick(view)
                            // 手動點擊時，只負責移除定時器，其餘不做，放手交給 onTargetDismissed
                            guideHandler.removeCallbacks(finishGuideRunnable)
                        }
                        override fun onTargetDismissed(view: com.getkeepsafe.taptargetview.TapTargetView?, userInitiated: Boolean) {
                            super.onTargetDismissed(view, userInitiated)
                            // 整個指引正式安全結束，再寫入 SharedPreferences
                            sharedPref.edit().putBoolean("IS_FIRST_TIME_HOME", false).apply()
                        }
                    }
                )
                // 3 秒後自動結束整個指引
                guideHandler.postDelayed(finishGuideRunnable, 3000)
            }
        }

        // 2️⃣ 第二步：歷史紀錄
        val startStep2 = {
            if (currentStep == 2) { // 確保只會執行一次
                SoundManager.playBubblePop()
                targetView2 = com.getkeepsafe.taptargetview.TapTargetView.showFor(this,
                    com.getkeepsafe.taptargetview.TapTarget.forView(cardHistory, "歷史紀錄", "查看過去的辨識結果")
                        .outerCircleColor(targetColorRes)
                        .targetCircleColor(android.R.color.white)
                        .titleTextColor(android.R.color.white)
                        .descriptionTextColor(android.R.color.white)
                        .cancelable(false).tintTarget(false).transparentTarget(true).drawShadow(true),
                    object : com.getkeepsafe.taptargetview.TapTargetView.Listener() {
                        override fun onTargetClick(view: com.getkeepsafe.taptargetview.TapTargetView?) {
                            super.onTargetClick(view)
                            // 手動點擊時，只負責移除定時器
                            guideHandler.removeCallbacks(jumpToStep3Runnable)
                        }
                        override fun onTargetDismissed(view: com.getkeepsafe.taptargetview.TapTargetView?, userInitiated: Boolean) {
                            super.onTargetDismissed(view, userInitiated)
                            // 無論是手動點還是時間到，元件消失時「統一」推進狀態並前往下一步
                            if (currentStep == 2) {
                                currentStep = 3
                                startStep3()
                            }
                        }
                    }
                )
                // 3 秒後自動跳到第三步
                guideHandler.postDelayed(jumpToStep3Runnable, 3000)
            }
        }

        // 1️⃣ 第一步：植物診斷
        targetView1 = com.getkeepsafe.taptargetview.TapTargetView.showFor(this,
            com.getkeepsafe.taptargetview.TapTarget.forView(cardDiagnose, "植物診斷", "點擊這裡開始辨識您的植物")
                .outerCircleColor(targetColorRes)
                .targetCircleColor(android.R.color.white)
                .titleTextColor(android.R.color.white)
                .descriptionTextColor(android.R.color.white)
                .cancelable(false).tintTarget(false).transparentTarget(true).drawShadow(true),
            object : com.getkeepsafe.taptargetview.TapTargetView.Listener() {
                override fun onTargetClick(view: com.getkeepsafe.taptargetview.TapTargetView?) {
                    super.onTargetClick(view)
                    // 手動點擊時，只負責移除定時器
                    guideHandler.removeCallbacks(jumpToStep2Runnable)
                }
                override fun onTargetDismissed(view: com.getkeepsafe.taptargetview.TapTargetView?, userInitiated: Boolean) {
                    super.onTargetDismissed(view, userInitiated)
                    // 消失時統一安全推進
                    if (currentStep == 1) {
                        currentStep = 2
                        startStep2()
                    }
                }
            }
        )
        // 3 秒後自動跳到第二步
        guideHandler.postDelayed(jumpToStep2Runnable, 3000)
    }

    override fun onStop() {
        super.onStop()
        SoundManager.stopWind()
        windHandler.removeCallbacks(windRunnable)
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

    override fun onDestroy() {
        super.onDestroy()
        windHandler.removeCallbacksAndMessages(null)
    }
}