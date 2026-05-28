package com.example.plantdoctor

import android.content.Context
import android.content.Intent
import android.content.res.ColorStateList // 🌟 新增
import android.graphics.Color // 🌟 新增
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.view.MotionEvent
import android.util.Log
import android.widget.ProgressBar
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.constraintlayout.widget.ConstraintLayout // 🌟 新增
import com.google.gson.Gson
import retrofit2.Call
import retrofit2.Callback
import retrofit2.Response

class HistoryProgressActivity : AppCompatActivity() {

    // 🌟 1. 建立風聲延遲計時器與任務（放在 onCreate 外面）
    private val windHandler = Handler(Looper.getMainLooper())
    private val windRunnable = Runnable {
        SoundManager.startWind() // 當按住滿 0.5 秒，正式吹起風聲
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_history_progress)

        // 🌟 核心新增：綁定最外層佈局與進度條
        val historyProgressRoot = findViewById<ConstraintLayout>(R.id.history_progress_root_layout)
        val progressBar = findViewById<ProgressBar>(R.id.progressBar_history)

        // 🌟 核心新增：召喚大總管換好背景色
        ThemeManager.applyTheme(
            context = this,
            rootLayout = historyProgressRoot
        )

        // 🌟 核心增強：根據目前使用者的主題，動態幫「歷史紀錄進度條」染上專屬主題顏色！
        val sharedPref = getSharedPreferences("PlantDoctor", Context.MODE_PRIVATE)
        val themeId = sharedPref.getInt("THEME_COLOR_ID", 0)
        val progressColorStr = when (themeId) {
            1 -> "#1565C0" // 海洋藍進度條
            2 -> "#D84315" // 暖陽橙進度條
            3 -> "#AD1457" // 蜜桃粉進度條
            else -> "#2E7D32" // 經典陽光綠進度條
        }
        progressBar.progressTintList = ColorStateList.valueOf(Color.parseColor(progressColorStr))

        // 1. 從小本本拿 Token
        val token = sharedPref.getString("token", null)

        if (token == null) {
            Toast.makeText(this, "登入已失效", Toast.LENGTH_SHORT).show()
            startActivity(Intent(this, LoginActivity::class.java))
            finish()
            return
        }

        // 2. 真的去拿歷史紀錄
        fetchHistoryAndNavigate(token, progressBar)
    }

    private fun fetchHistoryAndNavigate(token: String, progressBar: ProgressBar) {
        val apiService = PlantApiService.create(token)

        apiService.getAllHistory().enqueue(object : Callback<HistoryResponse> {
            override fun onResponse(call: Call<HistoryResponse>, response: Response<HistoryResponse>) {
                if (response.isSuccessful) {
                    progressBar.progress = 100

                    // 把拿到的資料轉成 JSON 傳給下一頁，省去下一頁再跑一次網路請求的時間
                    val historyDataJson = Gson().toJson(response.body()?.data)

                    val intent = Intent(this@HistoryProgressActivity, HistoryListActivity::class.java)
                    intent.putExtra("HISTORY_DATA", historyDataJson)
                    startActivity(intent)
                    finish()
                } else {
                    Log.e("HistoryProgress", "Error: ${response.code()}")
                    Toast.makeText(this@HistoryProgressActivity, "獲取紀錄失敗", Toast.LENGTH_SHORT).show()
                    finish()
                }
            }

            override fun onFailure(call: Call<HistoryResponse>, t: Throwable) {
                Log.e("HistoryProgress", "Failure: ${t.message}")
                Toast.makeText(this@HistoryProgressActivity, "連線超時", Toast.LENGTH_SHORT).show()
                finish()
            }
        })
    }

    // 🌟 全螢幕長按雷達，判定長按 0.5 秒才吹風
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