package com.example.plantdoctor

import android.content.Intent
import android.os.Bundle
import android.os.CountDownTimer
import android.widget.ProgressBar
import androidx.appcompat.app.AppCompatActivity

class HistoryProgressActivity : AppCompatActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_history_progress)

        val progressBar = findViewById<ProgressBar>(R.id.progressBar_history)

        // 2秒自動跳轉邏輯
        object : CountDownTimer(2000, 20) {
            override fun onTick(millisUntilFinished: Long) {
                val progress = ((2000 - millisUntilFinished) / 20).toInt()
                progressBar.progress = progress
            }

            override fun onFinish() {
                progressBar.progress = 100
                // 成功後跳轉到第十頁
                val intent = Intent(this@HistoryProgressActivity, HistoryListActivity::class.java)
                startActivity(intent)
                finish()
            }
        }.start()
    }
}