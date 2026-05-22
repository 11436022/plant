package com.example.plantdoctor

import android.content.Intent
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.view.MotionEvent
import android.widget.Button
import android.widget.ImageButton
import androidx.appcompat.app.AppCompatActivity
import com.getkeepsafe.taptargetview.TapTarget
import com.getkeepsafe.taptargetview.TapTargetView

class HomeActivity : AppCompatActivity() {

    private val windHandler = Handler(Looper.getMainLooper())
    private val windRunnable = Runnable {
        SoundManager.startWind()
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_home)

        // 1. 綁定元件
        val btnDiagnose: Button = findViewById(R.id.btn_diagnose)
        val btnHistory: Button = findViewById(R.id.btn_history)
        val btnSettings: ImageButton = findViewById(R.id.btn_settings)

        // 2. 按鈕點擊事件
        btnDiagnose.setOnClickListener {
            SoundManager.playBubblePop()
            val intent = Intent(this, UploadActivity::class.java)
            startActivity(intent)
        }

        btnHistory.setOnClickListener {
            SoundManager.playBubblePop()
            val intent = Intent(this, HistoryListActivity::class.java)
            startActivity(intent)
        }

        btnSettings.setOnClickListener {
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
                            btnSettings, "第三步：個人設定", "在這裡查看個人資料、帳號密碼，或是調整 App 的基礎設定。"
                        ).outerCircleColor(targetColorRes) // 🌟 這裡改用標準 .outerCircleColor() 傳入資源 ID
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
                            btnHistory, "第二步：查詢病例", "查看過去所有的植物診斷報告與觀察日記，掌握植物健康歷程。"
                        ).outerCircleColor(targetColorRes) // 🌟 這裡改用標準 .outerCircleColor()
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
                    btnDiagnose, "第一步：診斷植物", "點擊這裡可以拍照或上傳植物照片，讓 AI 馬上幫你分析病害！"
                ).outerCircleColor(targetColorRes) // 🌟 這裡改用標準 .outerCircleColor()
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