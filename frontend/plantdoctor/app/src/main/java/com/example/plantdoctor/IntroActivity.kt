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

        // 1. 綁定 IntroAdapter
        val adapter = IntroAdapter()
        viewPagerIntro.adapter = adapter

        // 2. 監聽 ViewPager2 的滑動狀態（動態改變按鈕文字）
        viewPagerIntro.registerOnPageChangeCallback(object : ViewPager2.OnPageChangeCallback() {
            override fun onPageSelected(position: Int) {
                super.onPageSelected(position)
                // 🌟 修正：因為有四頁，當 position == 3 時代表第四頁（最後一頁）
                if (position == 3) {
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
            // 🌟 修正：小於 3 時（也就是第 1、2、3 頁），點擊自動滑到下一頁
            if (currentItem < 3) {
                viewPagerIntro.setCurrentItem(currentItem + 1, true)
            } else {
                // 紀錄「我已經看過介紹了」，下次開機不要再秀給我看
                val sharedPref = getSharedPreferences("PlantDoctor", 0)
                sharedPref.edit().putBoolean("is_first_open", false).apply()

                // 如果已經是第四頁（開始使用），執行跳轉登入頁
                val intent = Intent(this, LoginActivity::class.java)
                startActivity(intent)
                finish() // 關閉介紹頁
            }
        }
    }

    // 保留原汁原味的全螢幕長按吹風聲雷達
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