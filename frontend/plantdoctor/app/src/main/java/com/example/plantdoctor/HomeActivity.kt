package com.example.plantdoctor

import android.content.Intent
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.view.MotionEvent
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

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_home)

        // 1. 綁定元件
        homeRoot = findViewById(R.id.home_root_layout)
        cardDiagnose = findViewById(R.id.card_diagnose)
        cardHistory = findViewById(R.id.card_history)
        cardSettings = findViewById(R.id.card_settings)

        // 2. 套用主題
        ThemeManager.applyTheme(this, homeRoot)

        // 3. 初始化音效管理器
        SoundManager.init(this)


        // 4. 按鈕點擊事件
        cardDiagnose.setOnClickListener {
            SoundManager.playBubblePop() // 使用 object 的方法
            val intent = Intent(this, UploadActivity::class.java) // 修正：應跳轉到上傳頁面
            startActivity(intent)
        }

        cardHistory.setOnClickListener {
            SoundManager.playBubblePop() // 使用 object 的方法
            val intent = Intent(this, HistoryListActivity::class.java)
            startActivity(intent)
        }

        cardSettings.setOnClickListener {
            SoundManager.playBubblePop() // 使用 object 的方法
            val intent = Intent(this, SettingsActivity::class.java)
            startActivity(intent)
        }

        val sharedPref = getSharedPreferences("PlantDoctor", MODE_PRIVATE)
        val isFirstTime = sharedPref.getBoolean("IS_FIRST_TIME_HOME", true)

        if (isFirstTime) {
            showTutorial()
        }
    }

    override fun onResume() {
        super.onResume()
        // 重新載入音效設定 (假設 SoundManager 內部會處理)
        // 如果 SoundManager 需要，可以新增一個 onResume 的處理方法
        SoundManager.startBGM()
    }

    private fun showTutorial() {
        val sequence = TapTargetSequence(this)
            .targets(
                TapTarget.forView(cardDiagnose, "植物診斷", "點擊這裡開始辨識您的植物")
                    .outerCircleColor(android.R.color.holo_green_dark)
                    .targetCircleColor(android.R.color.white)
                    .titleTextColor(android.R.color.white)
                    .descriptionTextColor(android.R.color.white)
                    .cancelable(false)
                    .tintTarget(false),
                TapTarget.forView(cardHistory, "歷史紀錄", "查看過去的辨識結果")
                    .outerCircleColor(android.R.color.holo_green_dark)
                    .targetCircleColor(android.R.color.white)
                    .titleTextColor(android.R.color.white)
                    .descriptionTextColor(android.R.color.white)
                    .cancelable(false)
                    .tintTarget(false),
                TapTarget.forView(cardSettings, "設定", "調整應用程式設定")
                    .outerCircleColor(android.R.color.holo_green_dark)
                    .targetCircleColor(android.R.color.white)
                    .titleTextColor(android.R.color.white)
                    .descriptionTextColor(android.R.color.white)
                    .cancelable(false)
                    .tintTarget(false)
            )
            .listener(object : TapTargetSequence.Listener {
                override fun onSequenceFinish() {
                    // 教學結束後，將旗標設為 false
                    val sharedPref = getSharedPreferences("PlantDoctor", MODE_PRIVATE)
                    sharedPref.edit().putBoolean("IS_FIRST_TIME_HOME", false).apply()
                }

                override fun onSequenceStep(lastTarget: TapTarget?, targetClicked: Boolean) {
                    // 每一步驟都播放音效
                    SoundManager.playBubblePop()
                }

                override fun onSequenceCanceled(lastTarget: TapTarget?) {}
            })
        sequence.start()
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