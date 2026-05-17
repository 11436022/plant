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
    private lateinit var tvFeedbackLink: TextView

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
        tvFeedbackLink = findViewById(R.id.tv_feedback_link)

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

        tvFeedbackLink.setOnClickListener {
            SoundManager.playBubblePop()
            // Toast.makeText(this, "已收到您的回饋請求！", Toast.LENGTH_SHORT).show()
            // 移除舊的 Toast，改為呼叫顯示選擇對話框的函式
            showDiagnosesSelectionDialog()
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

                    // --- 核心 UI 顯示邏輯 ---
                    // 檢查是否有使用者修正過的狀態
                    if (!data.user_corrected_status.isNullOrEmpty()) {
                        // 如果有，優先顯示使用者修正的結果
                        tvDiseaseName.text = data.user_corrected_status
                        tvDiseaseName.setTextColor(Color.parseColor("#2E7D32")) // 設定為代表「已確認」的綠色
                        tvFeedbackLink.visibility = android.view.View.GONE // 隱藏回饋按鈕
                    } else {
                        // 如果沒有，才顯示 AI 的原始診斷結果
                        tvDiseaseName.text = data.status_name
                        // 這裡可以根據需要，加入基於 confidence 的顏色判斷
                        tvDiseaseName.setTextColor(Color.RED) // 暫時預設為紅色
                        tvFeedbackLink.visibility = android.view.View.VISIBLE // 顯示回饋按鈕
                    }

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

    /**
     * 顯示一個對話框，其中包含從後端獲取的所有可選病症列表。
     */
    private fun showDiagnosesSelectionDialog() {
        // 建立一個簡單的 "載入中" 對話框
        val loadingDialog = AlertDialog.Builder(this)
            .setView(R.layout.dialog_loading) // 假設你有一個簡單的載入中佈局
            .setCancelable(false)
            .create()
        loadingDialog.show()

        val sharedPref = getSharedPreferences("PlantDoctor", Context.MODE_PRIVATE)
        val token = sharedPref.getString("token", "") ?: ""

        // 呼叫我們在 PlantApiService 中定義的新 API
        PlantApiService.create(token).getDiagnoses().enqueue(object : Callback<DiagnosesResponse> {
            override fun onResponse(call: Call<DiagnosesResponse>, response: Response<DiagnosesResponse>) {
                loadingDialog.dismiss() // 無論成功或失敗，都先關閉載入對話框

                if (response.isSuccessful) {
                    val diagnoses = response.body()?.data ?: emptyList()
                    if (diagnoses.isEmpty()) {
                        Toast.makeText(this@HistoryDetailActivity, "無法獲取診斷列表", Toast.LENGTH_SHORT).show()
                        return
                    }

                    // 將 List<DiagnosisItem> 轉換為 List<String> 以便顯示
                    val items = diagnoses.map { it.name }.toTypedArray()

                    // 建立並顯示選項列表對話框
                    AlertDialog.Builder(this@HistoryDetailActivity)
                        .setTitle("回報診斷結果")
                        .setItems(items) { dialog, which ->
                            // "which" 參數就是使用者點擊的項目的索引
                            val selectedDiagnosis = items[which]
                            
                            // 建立請求主體
                            val request = PatchDiaryRequest(user_corrected_status = selectedDiagnosis)

                            // 呼叫 PATCH API
                            PlantApiService.create(token).patchDiary(diaryId, request).enqueue(object : Callback<GenericResponse> {
                                override fun onResponse(call: Call<GenericResponse>, response: Response<GenericResponse>) {
                                    if (response.isSuccessful) {
                                        Toast.makeText(this@HistoryDetailActivity, "回饋已提交，感謝您！", Toast.LENGTH_LONG).show()

                                        // --- 樂觀更新 UI ---
                                        // 1. 立即將畫面上顯示的病名更新為使用者選擇的結果
                                        tvDiseaseName.text = selectedDiagnosis
                                        // 2. 改變文字顏色，以表示這是一個「已確認/已修正」的狀態 (改為較中性的綠色)
                                        tvDiseaseName.setTextColor(Color.parseColor("#2E7D32"))
                                        // 3. 隱藏「診斷結果有誤？」的按鈕，因為已經修正過了
                                        tvFeedbackLink.visibility = android.view.View.GONE

                                    } else {
                                        Toast.makeText(this@HistoryDetailActivity, "提交失敗: ${response.code()}", Toast.LENGTH_SHORT).show()
                                    }
                                }

                                override fun onFailure(call: Call<GenericResponse>, t: Throwable) {
                                    Toast.makeText(this@HistoryDetailActivity, "提交失敗: 網路連線問題", Toast.LENGTH_SHORT).show()
                                }
                            })
                        }
                        .setNegativeButton("取消", null)
                        .show()

                } else {
                    Toast.makeText(this@HistoryDetailActivity, "獲取列表失敗: ${response.code()}", Toast.LENGTH_SHORT).show()
                }
            }

            override fun onFailure(call: Call<DiagnosesResponse>, t: Throwable) {
                loadingDialog.dismiss()
                Toast.makeText(this@HistoryDetailActivity, "網路連線問題", Toast.LENGTH_SHORT).show()
            }
        })
    }
}