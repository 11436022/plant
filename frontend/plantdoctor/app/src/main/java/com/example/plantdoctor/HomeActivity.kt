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

        // 🌟 定義 3 秒時間到的自動跳轉指令 (Runnable)
        val jumpToStep2Runnable = Runnable { targetView1?.dismiss(true) }
        val jumpToStep3Runnable = Runnable { targetView2?.dismiss(true) }
        val finishGuideRunnable = Runnable { targetView3?.dismiss(true) }

        // 3️⃣ 第三步：設定
        val startStep3 = {
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
                        guideHandler.removeCallbacks(finishGuideRunnable) // 被手動點擊了，就取消定時器
                        sharedPref.edit().putBoolean("IS_FIRST_TIME_HOME", false).apply()
                    }
                    override fun onTargetDismissed(view: com.getkeepsafe.taptargetview.TapTargetView?, userInitiated: Boolean) {
                        super.onTargetDismissed(view, userInitiated)
                        sharedPref.edit().putBoolean("IS_FIRST_TIME_HOME", false).apply()
                    }
                }
            )
            // 3 秒後自動結束整個指引
            guideHandler.postDelayed(finishGuideRunnable, 3000)
        }

        // 2️⃣ 第二步：歷史紀錄
        val startStep2 = {
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
                        guideHandler.removeCallbacks(jumpToStep3Runnable) // 手動點擊，取消這步的定時
                        startStep3()
                    }
                    override fun onTargetDismissed(view: com.getkeepsafe.taptargetview.TapTargetView?, userInitiated: Boolean) {
                        super.onTargetDismissed(view, userInitiated)
                        startStep3() // 3 秒時間到觸發消失後，自動進入下一步
                    }
                }
            )
            // 3 秒後自動跳到第三步
            guideHandler.postDelayed(jumpToStep3Runnable, 3000)
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
                    guideHandler.removeCallbacks(jumpToStep2Runnable) // 手動點擊，取消這步的定時
                    startStep2()
                }
                override fun onTargetDismissed(view: com.getkeepsafe.taptargetview.TapTargetView?, userInitiated: Boolean) {
                    super.onTargetDismissed(view, userInitiated)
                    startStep2() // 3 秒時間到觸發消失後，自動進入下一步
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