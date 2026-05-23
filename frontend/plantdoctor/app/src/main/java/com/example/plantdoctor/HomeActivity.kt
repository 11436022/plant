package com.example.plantdoctor

import android.content.Intent
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.view.MotionEvent
import android.widget.Button
import android.widget.ImageButton
import androidx.appcompat.app.AppCompatActivity
import androidx.constraintlayout.widget.ConstraintLayout // 🌟 新增
import com.getkeepsafe.taptargetview.TapTarget
import com.getkeepsafe.taptargetview.TapTargetView

class HomeActivity : AppCompatActivity() {

    private val windHandler = Handler(Looper.getMainLooper())
    private val windRunnable = Runnable {
        SoundManager.startWind()
    }

    // 🌟 全域宣告元件，方便在 onCreate 與 onResume 都能安全存取
    private lateinit var homeRoot: ConstraintLayout
    private lateinit var cardDiagnose: androidx.cardview.widget.CardView
    private lateinit var cardHistory: androidx.cardview.widget.CardView
    private lateinit var cardSettings: androidx.cardview.widget.CardView
    private lateinit var btnDiagnose: Button
    private lateinit var btnHistory: Button
    private lateinit var btnSettings: ImageButton

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_home)

        // 1. 綁定元件
        homeRoot = findViewById(R.id.home_root_layout)
        btnDiagnose = findViewById(R.id.btn_diagnose)
        btnHistory = findViewById(R.id.btn_history)
        btnSettings = findViewById(R.id.btn_settings)
        cardDiagnose = findViewById(R.id.card_diagnose)
        cardHistory = findViewById(R.id.card_history)
        cardSettings = findViewById(R.id.card_settings)

        // 2. 按鈕點擊事件 (改由 CardView 觸發)
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

        // ==========================================================
        // 🌟 新手引導核心：獨立接力完全修復版（使用系統內建綠色資源，徹底解報錯）
        // ==========================================================
        val sharedPref = getSharedPreferences("PlantDoctor", MODE_PRIVATE)
        val isFirstTime = sharedPref.getBoolean("IS_FIRST_TIME_HOME", true)

        if (isFirstTime) {
            // 🌟 核心修正：直接使用 Android 系統自帶的綠色資源 ID，完美繞過 Lint 檢查
            val targetColorRes = android.R.color.holo_green_dark
            val autoJumpHandler = Handler(Looper.getMainLooper())

            // 宣告三個步驟的 View 實體指標
            var targetView1: TapTargetView? = null
            var targetView2: TapTargetView? = null
            var targetView3: TapTargetView? = null

            // 用來標記該步驟是否已經去過下一步，避免手動點擊+自動計時同時觸發導致重疊
            var hasMovedToStep2 = false
            var hasMovedToStep3 = false

            // 定義 3 秒時間到的定時關閉任務
            val jumpToStep2Runnable = Runnable { targetView1?.dismiss(true) }
            val jumpToStep3Runnable = Runnable { targetView2?.dismiss(true) }
            val finishSequenceRunnable = Runnable { targetView3?.dismiss(true) }

            // ----------------------------------------
            // 第三步：個人設定的啟動函式
            // ----------------------------------------
            val startStep3 = {
                if (!hasMovedToStep3) {
                    hasMovedToStep3 = true
                    SoundManager.playBubblePop()
                    targetView3 = TapTargetView.showFor(this,
                        TapTarget.forView(
                            cardSettings, "第三步：個人設定", "在這裡查看個人資料、帳號密碼，或是調整 App 的基礎設定。"
                        ).outerCircleColor(targetColorRes) // 這裡改用標準 .outerCircleColor() 傳入資源 ID
                            .targetCircleColor(android.R.color.white)
                            .titleTextSize(24)
                            .descriptionTextSize(16)
                            .textColor(android.R.color.white)
                            .transparentTarget(true)
                            .drawShadow(true)
                            .cancelable(false),
                        object : TapTargetView.Listener() {
                            override fun onTargetClick(view: TapTargetView?) {
                                super.onTargetClick(view)
                                autoJumpHandler.removeCallbacks(finishSequenceRunnable)
                                sharedPref.edit().putBoolean("IS_FIRST_TIME_HOME", false).apply()
                            }
                            override fun onTargetDismissed(view: TapTargetView?, userInitiated: Boolean) {
                                super.onTargetDismissed(view, userInitiated)
                                sharedPref.edit().putBoolean("IS_FIRST_TIME_HOME", false).apply()
                            }
                        }
                    )
                    autoJumpHandler.postDelayed(finishSequenceRunnable, 3000)
                }
            }

            // ----------------------------------------
            // 第二步：查詢病例的啟動函式
            // ----------------------------------------
            val startStep2 = {
                if (!hasMovedToStep2) {
                    hasMovedToStep2 = true
                    SoundManager.playBubblePop()
                    targetView2 = TapTargetView.showFor(this,
                        TapTarget.forView(
                            cardHistory, "第二步：查詢病例", "查看過去所有的植物診斷報告與觀察日記，掌握植物健康歷程。"
                        ).outerCircleColor(targetColorRes) // 這裡改用標準 .outerCircleColor()
                            .targetCircleColor(android.R.color.white)
                            .titleTextSize(24)
                            .descriptionTextSize(16)
                            .textColor(android.R.color.white)
                            .transparentTarget(true)
                            .drawShadow(true)
                            .cancelable(false),
                        object : TapTargetView.Listener() {
                            override fun onTargetClick(view: TapTargetView?) {
                                super.onTargetClick(view)
                                autoJumpHandler.removeCallbacks(jumpToStep3Runnable)
                                startStep3()
                            }
                            override fun onTargetDismissed(view: TapTargetView?, userInitiated: Boolean) {
                                super.onTargetDismissed(view, userInitiated)
                                startStep3()
                            }
                        }
                    )
                    autoJumpHandler.postDelayed(jumpToStep3Runnable, 3000)
                }
            }

            // ----------------------------------------
            // 第一步：診斷植物（一進畫面最先啟動）
            // ----------------------------------------
            targetView1 = TapTargetView.showFor(this,
                TapTarget.forView(
                    cardDiagnose, "第一步：診斷植物", "點擊這裡可以拍照或上傳植物照片，讓 AI 馬上幫你分析病害！"
                ).outerCircleColor(targetColorRes) // 這裡改用標準 .outerCircleColor()
                    .targetCircleColor(android.R.color.white)
                    .titleTextSize(24)
                    .descriptionTextSize(16)
                    .textColor(android.R.color.white)
                    .transparentTarget(true)
                    .drawShadow(true)
                    .cancelable(false),
                object : TapTargetView.Listener() {
                    override fun onTargetClick(view: TapTargetView?) {
                        super.onTargetClick(view)
                        autoJumpHandler.removeCallbacks(jumpToStep2Runnable)
                        startStep2()
                    }
                    override fun onTargetDismissed(view: TapTargetView?, userInitiated: Boolean) {
                        super.onTargetDismissed(view, userInitiated)
                        startStep2()
                    }
                }
            )
            autoJumpHandler.postDelayed(jumpToStep2Runnable, 3000)
        }
    } // onCreate 結束

    // 🌟 核心新增：在 onResume 觸發大總管換色，確保從設定頁按返回時能秒速變色
    override fun onResume() {
        super.onResume()
        ThemeManager.applyTheme(
            context = this,
            rootLayout = homeRoot,
            mainButtons = listOf(btnDiagnose, btnHistory) // 只讓這兩個功能按鈕跟隨主題變色
            // imageButtons 留空不傳，這樣你的圖片按鈕就不會被改動到囉！
        )
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