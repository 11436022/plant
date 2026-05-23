package com.example.plantdoctor

import android.content.Intent
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.view.MotionEvent
import android.widget.Button
import androidx.appcompat.app.AppCompatActivity
import androidx.viewpager2.widget.ViewPager2

class IntroActivity : AppCompatActivity() {

    private val windHandler = Handler(Looper.getMainLooper())
    private val windRunnable = Runnable {
        SoundManager.startWind()
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_intro)

        val viewPagerIntro = findViewById<ViewPager2>(R.id.viewPager_intro)
        val btnStart = findViewById<Button>(R.id.btn_start)

        // 1. 綁定剛剛寫好的 IntroAdapter
        val adapter = IntroAdapter()
        viewPagerIntro.adapter = adapter

        // 2. 監聽 ViewPager2 的滑動狀態（動態改變按鈕文字）
        viewPagerIntro.registerOnPageChangeCallback(object : ViewPager2.OnPageChangeCallback() {
            override fun onPageSelected(position: Int) {
                super.onPageSelected(position)
                // 索引從 0 開始，所以 position == 2 代表第三頁（最後一頁）
                if (position == 2) {
                    btnStart.text = "開始使用"
                } else {
                    btnStart.text = "下一頁"
                }
            }
        })

        // 3. 設定按鈕的點擊智慧指令
        btnStart.setOnClickListener {
            SoundManager.playBubblePop() // 播放清脆泡泡音

            val currentItem = viewPagerIntro.currentItem
            if (currentItem < 2) {
                // 如果不是最後一頁，點擊就自動平滑滑到下一頁
                viewPagerIntro.setCurrentItem(currentItem + 1, true)
            } else {
                // 🌟 新增：紀錄「我已經看過介紹了」，下次開機不要再秀給我看
                val sharedPref = getSharedPreferences("PlantDoctor", 0)
                sharedPref.edit().putBoolean("is_first_open", false).apply()

                // 如果已經是最後一頁（開始使用），執行跳轉登入頁
                val intent = Intent(this, LoginActivity::class.java)
                startActivity(intent)
                finish() // 關閉介紹頁
            }
        }
    }

    // 🌟 保留原汁原味的全螢幕長按吹風聲雷達
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