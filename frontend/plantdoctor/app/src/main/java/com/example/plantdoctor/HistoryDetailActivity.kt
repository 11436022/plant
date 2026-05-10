package com.example.plantdoctor

import android.content.Context
import android.graphics.Color
import android.os.Bundle
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
            showDeleteConfirmDialog()
        }

        btnBack.setOnClickListener {
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
                }
            }
            override fun onFailure(call: Call<DetailDetailResponse>, t: Throwable) {
                Toast.makeText(this@HistoryDetailActivity, "載入失敗", Toast.LENGTH_SHORT).show()
            }
        })
    }

    private fun showDeleteConfirmDialog() {
        AlertDialog.Builder(this)
            .setTitle("刪除病例")
            .setMessage("確定要永久刪除這筆診斷紀錄嗎？")
            .setPositiveButton("確定") { _, _ -> executeDelete() }
            .setNegativeButton("取消", null)
            .show()
    }

    private fun executeDelete() {
        val sharedPref = getSharedPreferences("PlantDoctor", Context.MODE_PRIVATE)
        val token = sharedPref.getString("token", "") ?: ""

        PlantApiService.create(token).deleteDiary(diaryId).enqueue(object : Callback<GenericResponse> {
            override fun onResponse(call: Call<GenericResponse>, response: Response<GenericResponse>) {
                if (response.isSuccessful) {
                    Toast.makeText(this@HistoryDetailActivity, "刪除成功", Toast.LENGTH_SHORT).show()
                    finish() // 關閉此頁
                }
            }
            override fun onFailure(call: Call<GenericResponse>, t: Throwable) {
                Toast.makeText(this@HistoryDetailActivity, "刪除失敗", Toast.LENGTH_SHORT).show()
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
}