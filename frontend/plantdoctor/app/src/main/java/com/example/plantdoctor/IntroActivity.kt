package com.example.plantdoctor

import android.content.Intent
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.view.MotionEvent
import android.widget.Button
import androidx.appcompat.app.AppCompatActivity

class IntroActivity : AppCompatActivity() {

    // 🌟 1. 建立風聲延遲計時器與任務（放在 onCreate 外面）
    private val windHandler = Handler(Looper.getMainLooper())
    private val windRunnable = Runnable {
        SoundManager.startWind() // 當按住滿 0.5 秒，正式吹起風聲
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_intro)

        // 1. 找到畫面上的按鈕
        val btnStart = findViewById<Button>(R.id.btn_start)

        // 2. 設定按鈕的點擊指令
        btnStart.setOnClickListener {
            // 🌟 核心修改：在跳轉前，先發出清脆的泡泡聲！
            SoundManager.playBubblePop()

            // 當按鈕被點擊時，執行跳轉
            val intent = Intent(this, LoginActivity::class.java)
            startActivity(intent)

            finish() // 關閉介紹頁
        }
    } // 👈 onCreate 的結尾

    // 🌟 2. 核心修改：全螢幕長按雷達，判定長按 0.5 秒才吹風
    override fun onTouchEvent(event: MotionEvent?): Boolean {
        if (event != null) {
            when (event.action) {
                MotionEvent.ACTION_DOWN -> {
                    // 手指一碰到螢幕任意處：先設定一個 0.5 秒後的鬧鐘
                    windHandler.postDelayed(windRunnable, 500)
                }
                MotionEvent.ACTION_UP, MotionEvent.ACTION_CANCEL -> {
                    // 手指一離開或滑開螢幕：
                    // 鎖 1：如果按不到 0.5 秒就放開，立刻取消鬧鐘（風聲就不會響）
                    windHandler.removeCallbacks(windRunnable)

                    // 鎖 2：如果風聲此時已經在播了，放開時就讓它安靜
                    SoundManager.stopWind()
                }
            }
        }
        return super.onTouchEvent(event)
    }

    // 🌟 3. 核心修改：離開畫面時，安全切斷風聲並復原計時器
    override fun onStop() {
        super.onStop()
        SoundManager.stopWind() // 離開這頁時強制關閉風聲
        windHandler.removeCallbacks(windRunnable) // 撤銷風聲鬧鐘
    }

    // 🌟 4. 銷毀畫面時清空計時器，防止記憶體洩漏
    override fun onDestroy() {
        super.onDestroy()
        windHandler.removeCallbacksAndMessages(null)
    }
}