package com.example.plantdoctor

import android.content.Context
import android.graphics.Color
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.view.MotionEvent
import android.util.Log
import android.widget.Button
import android.widget.ImageButton
import android.widget.ImageView
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import com.bumptech.glide.Glide
import retrofit2.Call
import retrofit2.Callback
import retrofit2.Response

class HistoryDetailActivity : AppCompatActivity() {

    private var diaryId: Int = -1

    // 對應 XML 的元件
    private lateinit var imgPlant: ImageView
    private lateinit var tvPlantName: TextView
    private lateinit var tvDiseaseName: TextView
    private lateinit var tvAdvice: TextView
    private lateinit var btnAction: Button
    private lateinit var btnBack: ImageButton

    // 🌟 1. 建立風聲延遲計時器與任務（放在 onCreate 外面）
    private val windHandler = Handler(Looper.getMainLooper())
    private val windRunnable = Runnable {
        SoundManager.startWind() // 當按住滿 0.5 秒，正式吹起風聲
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_result) // 直接複用你的診斷 UI

        diaryId = intent.getIntExtra("DIARY_ID", -1)

        initViews()
        setupLogic()
        fetchData()
    }

    private fun initViews() {
        imgPlant = findViewById(R.id.img_result_plant)
        tvPlantName = findViewById(R.id.tv_plant_name)
        tvDiseaseName = findViewById(R.id.tv_disease_name)
        tvAdvice = findViewById(R.id.tv_advice)
        btnAction = findViewById(R.id.btn_save_report) // 複用這個按鈕
        btnBack = findViewById(R.id.btn_back_home)

        // 修改標題（XML 裡的 tv_title）
        findViewById<TextView>(R.id.tv_title)?.text = "病例詳情"
    }

    private fun setupLogic() {
        // 將原本「儲存」按鈕改為「刪除」
        btnAction.text = "刪除此筆病例"
        btnAction.backgroundTintList = getColorStateList(android.R.color.holo_red_light)

        btnAction.setOnClickListener {
            // 🌟 核心修改：點擊刪除按鈕時播放泡泡聲
            SoundManager.playBubblePop()
            // 放棄使用 AlertDialog，直接執行刪除
            executeDelete()
        }

        btnBack.setOnClickListener {
            // 🌟 核心修改：點擊返回按鈕時播放泡泡聲
            SoundManager.playBubblePop()
            finish()
        }
    }

    private fun fetchData() {
        val sharedPref = getSharedPreferences("PlantDoctor", Context.MODE_PRIVATE)
        val token = sharedPref.getString("token", "") ?: ""

        PlantApiService.create(token).getDiaryDetail(diaryId).enqueue(object : Callback<DetailDetailResponse> {
            override fun onResponse(call: Call<DetailDetailResponse>, response: Response<DetailDetailResponse>) {
                if (response.isSuccessful) {
                    val data = response.body()?.data ?: return

                    // 填入資料
                    tvPlantName.text = "植物：${data.crop_name}"
                    tvDiseaseName.text = data.status_name

                    // 組合建議與處理方式
                    val fullAdvice = "【專家建議】\n${data.suggestion ?: "尚無建議"}\n\n" +
                            "【處理方式】\n${data.treatment ?: "請諮詢專業人員"}"
                    tvAdvice.text = fullAdvice

                    // 圖片處理
                    val finalUrl = fixImageUrl(data.image_url)
                    Glide.with(this@HistoryDetailActivity)
                        .load(finalUrl)
                        .placeholder(android.R.drawable.ic_menu_gallery)
                        .into(imgPlant)

                    // 【新增】處理使用者筆記的顯示
                    val etUserNote = findViewById<TextView>(R.id.et_user_note)
                    if (!data.user_note.isNullOrEmpty()) {
                        etUserNote.visibility = android.view.View.VISIBLE
                        etUserNote.text = data.user_note
                        // 移除輸入框樣式，讓它看起來像普通文字
                        etUserNote.background = null
                        etUserNote.isFocusable = false
                        etUserNote.isClickable = false
                    } else {
                        // 如果沒有筆記，就隱藏這個元件
                        etUserNote.visibility = android.view.View.GONE
                    }
                }
            }
            override fun onFailure(call: Call<DetailDetailResponse>, t: Throwable) {
                Toast.makeText(this@HistoryDetailActivity, "載入失敗", Toast.LENGTH_SHORT).show()
            }
        })
    }

    private fun executeDelete() {
        val sharedPref = getSharedPreferences("PlantDoctor", Context.MODE_PRIVATE)
        val token = sharedPref.getString("token", "") ?: ""

        PlantApiService.create(token).deleteDiary(diaryId).enqueue(object : Callback<GenericResponse> {
            override fun onResponse(call: Call<GenericResponse>, response: Response<GenericResponse>) {
                if (response.isSuccessful) {
                    Toast.makeText(this@HistoryDetailActivity, "刪除成功", Toast.LENGTH_SHORT).show()
                    setResult(RESULT_OK)
                    finish()
                } else {
                    Toast.makeText(this@HistoryDetailActivity, "刪除失敗: ${response.code()}", Toast.LENGTH_SHORT).show()
                }
            }

            override fun onFailure(call: Call<GenericResponse>, t: Throwable) {
                Toast.makeText(this@HistoryDetailActivity, "刪除失敗: 網路連線問題", Toast.LENGTH_SHORT).show()
            }
        })
    }

    private fun fixImageUrl(rawUrl: String): String {
        var url = rawUrl.replace("127.0.0.1", "10.0.2.2").replace("localhost", "10.0.2.2")
        val keyword = "static/"
        if (url.contains(keyword)) {
            val startIndex = url.indexOf(keyword)
            val firstSlash = url.indexOf("/", 8)
            if (firstSlash != -1) {
                val baseUrl = url.substring(0, firstSlash + 1)
                return baseUrl + url.substring(startIndex)
            }
        }
        return url
    }

    // 🌟 2. 核心修改：全螢幕長按雷達，判定長按 0.5 秒才吹風
    override fun onTouchEvent(event: MotionEvent?): Boolean {
        if (event != null) {
            when (event.action) {
                MotionEvent.ACTION_DOWN -> {
                    // 手指一碰到螢幕任意處：先設定一個 0.5 秒後的鬧鐘
                    windHandler.postDelayed(windRunnable, 500)
                }
                MotionEvent.ACTION_UP, MotionEvent.ACTION_CANCEL -> {
                    // 手指一離開或滑開螢幕：撤銷鬧鐘，停止風聲
                    windHandler.removeCallbacks(windRunnable)
                    SoundManager.stopWind()
                }
            }
        }
        return super.onTouchEvent(event)
    }

    // 🌟 3. 核心修改：離開畫面時，安全切斷風聲並復原計時器
    override fun onStop() {
        super.onStop()
        SoundManager.stopWind()
        windHandler.removeCallbacks(windRunnable)
    }

    // 🌟 4. 銷毀畫面時清空計時器，防止記憶體洩漏
    override fun onDestroy() {
        super.onDestroy()
        windHandler.removeCallbacksAndMessages(null)
    }
}