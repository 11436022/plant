package com.example.plantdoctor

import android.content.Context
import android.content.Intent
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
import androidx.constraintlayout.widget.ConstraintLayout
import com.bumptech.glide.Glide
import com.getkeepsafe.taptargetview.TapTarget
import com.getkeepsafe.taptargetview.TapTargetView
import retrofit2.Call
import retrofit2.Callback
import retrofit2.Response

class HistoryDetailActivity : AppCompatActivity() {

    private var diaryId: Int = -1
    private var currentImageUrl: String? = null // 🌟 用來記住下載完的真正網址

    // 對應 XML 的元件
    private lateinit var imgPlant: ImageView
    private lateinit var tvPlantName: TextView
    private lateinit var tvDiseaseName: TextView
    private lateinit var tvAdvice: TextView
    private lateinit var btnAction: Button
    private lateinit var btnBack: ImageButton
    private lateinit var tvFeedbackLink: TextView

    // 風聲延遲計時器與任務
    private val windHandler = Handler(Looper.getMainLooper())
    private val windRunnable = Runnable {
        SoundManager.startWind()
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_result) // 直接複用診斷 UI

        diaryId = intent.getIntExtra("DIARY_ID", -1)

        initViews()
        setupLogic()
        fetchData()

        // 🌟 啟動專屬於「病例詳情頁」的新手教學引導
        setupHistoryDetailGuide()
    }

    private fun initViews() {
        // 1. 綁定元件
        val resultRoot = findViewById<ConstraintLayout>(R.id.result_root_layout)
        val tvMainTitle = findViewById<TextView>(R.id.tv_title)

        imgPlant = findViewById(R.id.img_result_plant)
        tvPlantName = findViewById(R.id.tv_plant_name)
        tvDiseaseName = findViewById(R.id.tv_disease_name)
        tvAdvice = findViewById(R.id.tv_advice)
        btnAction = findViewById(R.id.btn_save_report) // 複用儲存按鈕來做刪除
        btnBack = findViewById(R.id.btn_back_home)
        tvFeedbackLink = findViewById(R.id.tv_feedback_link)

        // 修改標題大字
        tvMainTitle?.text = "病例詳情"

        // 🌟 召喚大總管精準換色：對齊 ResultActivity 丟入大總管，返回箭頭 btnBack 才會完美顯現換色！
        ThemeManager.applyTheme(
            context = this,
            rootLayout = resultRoot,
            titles = listOf(tvMainTitle),
            imageButtons = listOf(btnBack) // 👈 讓返回箭頭顯色不隱形！
        )
    }

    private fun setupLogic() {
        // 將原本「儲存」按鈕改為「刪除」
        btnAction.text = "刪除此筆病例"
        btnAction.backgroundTintList = getColorStateList(android.R.color.holo_red_light)

        btnAction.setOnClickListener {
            SoundManager.playBubblePop()
            executeDelete()
        }

        // 🌟 點擊返回：對齊 ResultActivity 的點擊 bubble 聲，直接 finish 退出返回上一頁清單
        btnBack.setOnClickListener {
            SoundManager.playBubblePop()
            finish()
        }

        // 🌟 點擊植物照片：完全對齊 ResultActivity 邏輯！直接跳轉到 ImagePreviewActivity 放大！
        imgPlant.setOnClickListener {
            if (!currentImageUrl.isNullOrEmpty()) {
                SoundManager.playBubblePop()
                val intent = Intent(this, ImagePreviewActivity::class.java).apply {
                    putExtra("IMAGE_PATH", currentImageUrl) // 丟入網址
                }
                startActivity(intent)
            }
        }

        tvFeedbackLink.setOnClickListener {
            SoundManager.playBubblePop()
            showDiagnosesSelectionDialog()
        }
    }

    private fun setupHistoryDetailGuide() {
        val sharedPref = getSharedPreferences("PlantDoctor", Context.MODE_PRIVATE)
        val isFirstTimeDetail = sharedPref.getBoolean("IS_FIRST_TIME_HISTORY_DETAIL", true)

        if (isFirstTimeDetail) {
            val targetColorRes = android.R.color.holo_green_dark
            val autoJumpHandler = Handler(Looper.getMainLooper())

            var targetView1: TapTargetView? = null
            val jumpToStep2Runnable = Runnable { targetView1?.dismiss(true) }

            targetView1 = TapTargetView.showFor(this,
                TapTarget.forView(
                    imgPlant, "點擊放大回顧", "點擊這張過去拍攝的照片，就能進入全螢幕模式，雙指放大縮小觀察病徵！"
                ).outerCircleColor(targetColorRes)
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
                        sharedPref.edit().putBoolean("IS_FIRST_TIME_HISTORY_DETAIL", false).apply()
                    }
                    override fun onTargetDismissed(view: TapTargetView?, userInitiated: Boolean) {
                        super.onTargetDismissed(view, userInitiated)
                        sharedPref.edit().putBoolean("IS_FIRST_TIME_HISTORY_DETAIL", false).apply()
                    }
                }
            )
            autoJumpHandler.postDelayed(jumpToStep2Runnable, 3000)
        }
    }

    private fun fetchData() {
        val sharedPref = getSharedPreferences("PlantDoctor", Context.MODE_PRIVATE)
        val token = sharedPref.getString("token", "") ?: ""

        // 呼叫假 API 的詳情接口
        PlantApiService.create(token).getDiaryDetail(diaryId).enqueue(object : Callback<DetailDetailResponse> {
            override fun onResponse(call: Call<DetailDetailResponse>, response: Response<DetailDetailResponse>) {
                if (response.isSuccessful) {
                    val data = response.body()?.data ?: return

                    tvPlantName.text = "植物：${data.crop_name ?: "無法辨識"}"

                    if (!data.user_corrected_status.isNullOrEmpty()) {
                        tvDiseaseName.text = "診斷：${data.user_corrected_status}"
                        tvDiseaseName.setTextColor(Color.parseColor("#2E7D32"))
                        tvFeedbackLink.visibility = android.view.View.GONE
                    } else {
                        tvDiseaseName.text = "診斷：${data.status_name ?: "未知"}"
                        tvDiseaseName.setTextColor(Color.RED)
                        tvFeedbackLink.visibility = android.view.View.VISIBLE
                    }

                    val fullAdvice = "【專家建議】\n${data.suggestion ?: "尚無建議"}\n\n" +
                            "【治療方法】\n${data.treatment ?: "請諮詢專業人員"}"
                    tvAdvice.text = fullAdvice

                    // 🌟 核心修正：直接保留原始網址，不再進行惡意的字串裁切，這樣網路圖片（Unsplash）跟快取圖就都能抓到了！
                    currentImageUrl = data.image_url

                    Glide.with(this@HistoryDetailActivity)
                        .load(currentImageUrl)
                        .placeholder(android.R.drawable.ic_menu_gallery)
                        .into(imgPlant)

                    // 隱藏不必要的輸入筆記框細節
                    val etUserNote = findViewById<TextView>(R.id.et_user_note)
                    if (!data.user_note.isNullOrEmpty()) {
                        etUserNote.visibility = android.view.View.VISIBLE
                        etUserNote.text = data.user_note
                        etUserNote.background = null
                        etUserNote.isFocusable = false
                        etUserNote.isClickable = false
                    } else {
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

    private fun showDiagnosesSelectionDialog() {
        val loadingDialog = AlertDialog.Builder(this)
            .setView(R.layout.dialog_loading)
            .setCancelable(false)
            .create()
        loadingDialog.show()

        val sharedPref = getSharedPreferences("PlantDoctor", Context.MODE_PRIVATE)
        val token = sharedPref.getString("token", "") ?: ""

        PlantApiService.create(token).getDiagnoses().enqueue(object : Callback<DiagnosesResponse> {
            override fun onResponse(call: Call<DiagnosesResponse>, response: Response<DiagnosesResponse>) {
                loadingDialog.dismiss()

                if (response.isSuccessful) {
                    val diagnoses = response.body()?.data ?: emptyList()
                    if (diagnoses.isEmpty()) {
                        Toast.makeText(this@HistoryDetailActivity, "無法獲取診斷列表", Toast.LENGTH_SHORT).show()
                        return
                    }

                    val items = diagnoses.map { it.name }.toTypedArray()

                    AlertDialog.Builder(this@HistoryDetailActivity)
                        .setTitle("回報診斷結果")
                        .setItems(items) { dialog, which ->
                            val selectedDiagnosis = items[which]
                            val request = PatchDiaryRequest(user_corrected_status = selectedDiagnosis)

                            PlantApiService.create(token).patchDiary(diaryId, request).enqueue(object : Callback<GenericResponse> {
                                override fun onResponse(call: Call<GenericResponse>, response: Response<GenericResponse>) {
                                    if (response.isSuccessful) {
                                        Toast.makeText(this@HistoryDetailActivity, "回饋已提交，感謝您！", Toast.LENGTH_LONG).show()
                                        tvDiseaseName.text = "診斷：$selectedDiagnosis"
                                        tvDiseaseName.setTextColor(Color.parseColor("#2E7D32"))
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