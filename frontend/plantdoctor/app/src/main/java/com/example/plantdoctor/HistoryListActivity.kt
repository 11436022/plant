package com.example.plantdoctor

import android.app.DatePickerDialog
import android.content.Context
import android.content.Intent
import android.graphics.Color
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.text.Editable
import android.text.TextWatcher
import android.util.Log
import android.view.LayoutInflater
import android.view.MotionEvent
import android.view.View
import android.view.ViewGroup
import android.widget.Button
import android.widget.EditText
import android.widget.ImageButton
import android.widget.ImageView
import android.widget.LinearLayout
import android.widget.TextView
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.constraintlayout.widget.ConstraintLayout
import androidx.recyclerview.widget.GridLayoutManager
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.bumptech.glide.Glide
import com.google.gson.annotations.SerializedName
import retrofit2.Call
import retrofit2.Callback
import retrofit2.Response
import java.text.SimpleDateFormat
import java.util.Calendar
import java.util.Date
import java.util.Locale

// 歷史紀錄資料模型
data class HistoryItem(
    @SerializedName("id") val id: Int,
    @SerializedName("crop_name") val crop_name: String?,
    @SerializedName("plant_tag") val plant_tag: String? = null,
    @SerializedName("created_at") val created_at: String,
    @SerializedName("status_name") val status_name: String?,
    @SerializedName("user_corrected_status") val user_corrected_status: String?,
    @SerializedName("image_url") val image_url: String,
    @SerializedName("suggestion") var suggestion: String? = null,
    @SerializedName("treatment") var treatment: String? = null,
    @SerializedName("user_note") val user_note: String?,
    var isExpanded: Boolean = false,
    @SerializedName("confidence") val confidence: Double? = null,
    @SerializedName("category") val category: String? = null,
    @SerializedName("requires_review") val requires_review: Boolean? = null,
    @SerializedName("grounding_source") val grounding_source: String? = null,
    @SerializedName("reference_source") val reference_source: String? = null,
    @SerializedName("reference_url") val reference_url: String? = null,
    @SerializedName("reference_record_id") val reference_record_id: String? = null
)

class HistoryListActivity : AppCompatActivity() {
    private lateinit var adapter: HistoryAdapter
    private val displayList = mutableListOf<HistoryItem>()
    private val fullHistoryList = mutableListOf<HistoryItem>()
    private var lastQuery: String = ""

    // 🗓️ 日期與月份篩選變數
    private var selectedDateFilter: String? = null
    private var selectedMonthFilter: String? = null
    private var selectedCropFilter: String? = null // 🌟 植物品類篩選變數 (null 代表全部)
    private lateinit var layoutCropChips: LinearLayout

    // 🌟 建立風聲延遲計時器與任務
    private val windHandler = Handler(Looper.getMainLooper())
    private val windRunnable = Runnable {
        SoundManager.startWind()
    }

    private val detailActivityLauncher = registerForActivityResult(ActivityResultContracts.StartActivityForResult()) { result ->
        if (result.resultCode == RESULT_OK) {
            fetchHistoryFromServer()
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_history_list)

        val historyListRoot = findViewById<ConstraintLayout>(R.id.history_list_root_layout)
        val btnBack = findViewById<ImageButton>(R.id.btn_back_home)
        val tvHistoryMainTitle = findViewById<TextView>(R.id.tv_history_title)

        // 套用全局主題
        ThemeManager.applyTheme(
            context = this,
            rootLayout = historyListRoot,
            titles = listOf(tvHistoryMainTitle),
            imageButtons = listOf(btnBack)
        )

        // 1. 返回按鈕
        btnBack.setOnClickListener {
            SoundManager.playBubblePop()
            finish()
        }

        // 2. 關鍵字與日期直接搜尋輸入框
        val etSearch = findViewById<EditText>(R.id.et_search)
        etSearch.addTextChangedListener(object : TextWatcher {
            override fun afterTextChanged(s: Editable?) {
                lastQuery = s.toString()
                filterList(lastQuery)
            }
            override fun beforeTextChanged(s: CharSequence?, start: Int, count: Int, after: Int) {}
            override fun onTextChanged(s: CharSequence?, start: Int, before: Int, count: Int) {}
        })

        // 3. 📅 日曆挑選器按鈕 (解決特定日期需要一直滑動的痛點)
        val btnPickDate = findViewById<ImageButton>(R.id.btn_pick_date)
        btnPickDate.setOnClickListener {
            SoundManager.playBubblePop()
            showDatePickerDialog()
        }

        // 4. 快捷月份標籤綁定
        layoutCropChips = findViewById(R.id.layout_crop_chips)
        setupFilterChips()

        // 5. 初始化 RecyclerView：升級為現代「雙欄美型拍立得相簿網格 (2-Column Grid)」
        val rvHistory = findViewById<RecyclerView>(R.id.rv_history_list)
        rvHistory.layoutManager = GridLayoutManager(this, 2)
        adapter = HistoryAdapter(displayList, detailActivityLauncher)
        rvHistory.adapter = adapter
    }

    override fun onResume() {
        super.onResume()
        fetchHistoryFromServer()
    }

    /**
     * 彈出日曆對話框，供使用者點選特定年月日
     */
    private fun showDatePickerDialog() {
        val calendar = Calendar.getInstance()
        val datePicker = DatePickerDialog(
            this,
            { _, year, month, dayOfMonth ->
                val chosenDate = String.format(Locale.getDefault(), "%04d-%02d-%02d", year, month + 1, dayOfMonth)
                applyCustomDateFilter(chosenDate)
            },
            calendar.get(Calendar.YEAR),
            calendar.get(Calendar.MONTH),
            calendar.get(Calendar.DAY_OF_MONTH)
        )
        datePicker.show()
    }

    /**
     * 設定快捷導覽膠囊標籤點擊邏輯 (全部 / 本月 / 上月 / 特定日期)
     */
    private fun setupFilterChips() {
        val chipAll = findViewById<TextView>(R.id.chip_filter_all)
        val chipThisMonth = findViewById<TextView>(R.id.chip_filter_this_month)
        val chipLastMonth = findViewById<TextView>(R.id.chip_filter_last_month)
        val chipCustomDate = findViewById<TextView>(R.id.chip_filter_custom_date)

        val resetChipStyles = {
            chipAll.setBackgroundResource(R.drawable.bg_chip_unselected)
            chipAll.setTextColor(Color.parseColor("#2E7D32"))
            chipThisMonth.setBackgroundResource(R.drawable.bg_chip_unselected)
            chipThisMonth.setTextColor(Color.parseColor("#2E7D32"))
            chipLastMonth.setBackgroundResource(R.drawable.bg_chip_unselected)
            chipLastMonth.setTextColor(Color.parseColor("#2E7D32"))
        }

        // 點擊【全部紀錄】
        chipAll.setOnClickListener {
            SoundManager.playBubblePop()
            resetChipStyles()
            chipAll.setBackgroundResource(R.drawable.bg_chip_selected)
            chipAll.setTextColor(Color.WHITE)
            chipCustomDate.visibility = View.GONE
            selectedDateFilter = null
            selectedMonthFilter = null
            selectedCropFilter = null
            refreshCropChipStyles()
            filterList(lastQuery)
        }

        // 點擊【本月】
        chipThisMonth.setOnClickListener {
            SoundManager.playBubblePop()
            resetChipStyles()
            chipThisMonth.setBackgroundResource(R.drawable.bg_chip_selected)
            chipThisMonth.setTextColor(Color.WHITE)
            chipCustomDate.visibility = View.GONE
            selectedDateFilter = null
            selectedMonthFilter = SimpleDateFormat("yyyy-MM", Locale.getDefault()).format(Date())
            filterList(lastQuery)
        }

        // 點擊【上月】
        chipLastMonth.setOnClickListener {
            SoundManager.playBubblePop()
            resetChipStyles()
            chipLastMonth.setBackgroundResource(R.drawable.bg_chip_selected)
            chipLastMonth.setTextColor(Color.WHITE)
            chipCustomDate.visibility = View.GONE
            val cal = Calendar.getInstance().apply { add(Calendar.MONTH, -1) }
            selectedDateFilter = null
            selectedMonthFilter = SimpleDateFormat("yyyy-MM", Locale.getDefault()).format(cal.time)
            filterList(lastQuery)
        }

        // 點擊【已選特定日期膠囊】清除篩選
        chipCustomDate.setOnClickListener {
            SoundManager.playBubblePop()
            chipCustomDate.visibility = View.GONE
            chipAll.performClick()
        }
    }

    /**
     * 套用特定日期篩選並更新頂部標籤狀態
     */
    private fun applyCustomDateFilter(formattedDate: String) {
        selectedDateFilter = formattedDate
        selectedMonthFilter = null

        val chipAll = findViewById<TextView>(R.id.chip_filter_all)
        val chipThisMonth = findViewById<TextView>(R.id.chip_filter_this_month)
        val chipLastMonth = findViewById<TextView>(R.id.chip_filter_last_month)
        val chipCustomDate = findViewById<TextView>(R.id.chip_filter_custom_date)

        chipAll.setBackgroundResource(R.drawable.bg_chip_unselected)
        chipAll.setTextColor(Color.parseColor("#2E7D32"))
        chipThisMonth.setBackgroundResource(R.drawable.bg_chip_unselected)
        chipThisMonth.setTextColor(Color.parseColor("#2E7D32"))
        chipLastMonth.setBackgroundResource(R.drawable.bg_chip_unselected)
        chipLastMonth.setTextColor(Color.parseColor("#2E7D32"))

        chipCustomDate.text = "📅 $formattedDate ✕"
        chipCustomDate.visibility = View.VISIBLE

        filterList(lastQuery)
    }

    /**
     * 核心多維度過濾演算法：同時支援植物名稱、病害、輸入日期、點選日期、月份過濾
     */
    private fun filterList(query: String) {
        val trimmedQuery = query.trim()

        val filtered = fullHistoryList.filter { item ->
            // 1. 關鍵字搜尋 (同時支援作物名、病害名、覆核名與日期字串)
            val matchesKeyword = if (trimmedQuery.isEmpty()) {
                true
            } else {
                (item.crop_name ?: "").contains(trimmedQuery, ignoreCase = true) ||
                (item.plant_tag ?: "").contains(trimmedQuery, ignoreCase = true) ||
                (item.status_name ?: "").contains(trimmedQuery, ignoreCase = true) ||
                (item.user_corrected_status?.contains(trimmedQuery, ignoreCase = true) == true) ||
                item.created_at.contains(trimmedQuery, ignoreCase = true)
            }

            // 2. 精準特定日期過濾 (YYYY-MM-DD)
            val matchesDate = if (selectedDateFilter.isNullOrBlank()) {
                true
            } else {
                item.created_at.contains(selectedDateFilter!!)
            }

            // 3. 月份快捷過濾 (YYYY-MM)
            val matchesMonth = if (selectedMonthFilter.isNullOrBlank()) {
                true
            } else {
                item.created_at.contains(selectedMonthFilter!!)
            }

            // 4. 🌟 植物品類過濾 (Crop Filter)
            val matchesCrop = if (selectedCropFilter.isNullOrBlank()) {
                true
            } else {
                (item.crop_name ?: "未知植物") == selectedCropFilter
            }

            matchesKeyword && matchesDate && matchesMonth && matchesCrop
        }

        displayList.clear()
        displayList.addAll(filtered)
        adapter.notifyDataSetChanged()

        // 空狀態提示視圖
        val layoutEmpty = findViewById<View>(R.id.layout_empty_state)
        layoutEmpty.visibility = if (filtered.isEmpty()) View.VISIBLE else View.GONE
    }

    private fun updateLists(newData: List<HistoryItem>) {
        fullHistoryList.clear()
        fullHistoryList.addAll(newData)
        buildDynamicCropChips()
        filterList(lastQuery)
    }

    /**
     * 🌟 動態建置目前使用者所擁有的植物膠囊標籤 (例如：🍋 檸檬 (5)、🍉 西瓜 (3))
     */
    private fun buildDynamicCropChips() {
        layoutCropChips.removeAllViews()

        // 統計每種植物的紀錄數量
        val cropCounts = mutableMapOf<String, Int>()
        fullHistoryList.forEach { item ->
            val name = item.crop_name?.takeIf { it.isNotBlank() } ?: "未知植物"
            cropCounts[name] = (cropCounts[name] ?: 0) + 1
        }

        val density = resources.displayMetrics.density
        val marginEndPx = (8 * density).toInt()
        val padHPx = (14 * density).toInt()
        val padVPx = (7 * density).toInt()

        cropCounts.forEach { (cropName, count) ->
            val chip = TextView(this).apply {
                val params = LinearLayout.LayoutParams(
                    LinearLayout.LayoutParams.WRAP_CONTENT,
                    LinearLayout.LayoutParams.WRAP_CONTENT
                ).apply {
                    setMargins(0, 0, marginEndPx, 0)
                }
                layoutParams = params
                setPadding(padHPx, padVPx, padHPx, padVPx)
                textSize = 13f
                text = "$cropName ($count)"
                tag = cropName

                if (selectedCropFilter == cropName) {
                    setBackgroundResource(R.drawable.bg_chip_selected)
                    setTextColor(Color.WHITE)
                } else {
                    setBackgroundResource(R.drawable.bg_chip_unselected)
                    setTextColor(Color.parseColor("#2E7D32"))
                }

                setOnClickListener {
                    SoundManager.playBubblePop()
                    if (selectedCropFilter == cropName) {
                        // 再次點擊取消篩選
                        selectedCropFilter = null
                    } else {
                        selectedCropFilter = cropName
                    }
                    refreshCropChipStyles()
                    filterList(lastQuery)
                }
            }
            layoutCropChips.addView(chip)
        }
    }

    private fun refreshCropChipStyles() {
        val chipAll = findViewById<TextView>(R.id.chip_filter_all)
        for (i in 0 until layoutCropChips.childCount) {
            val child = layoutCropChips.getChildAt(i) as? TextView ?: continue
            val cropTag = child.tag as? String
            if (cropTag == selectedCropFilter) {
                child.setBackgroundResource(R.drawable.bg_chip_selected)
                child.setTextColor(Color.WHITE)
            } else {
                child.setBackgroundResource(R.drawable.bg_chip_unselected)
                child.setTextColor(Color.parseColor("#2E7D32"))
            }
        }

        if (selectedCropFilter != null) {
            chipAll.setBackgroundResource(R.drawable.bg_chip_unselected)
            chipAll.setTextColor(Color.parseColor("#2E7D32"))
        }
    }

    private fun fetchHistoryFromServer() {
        val sharedPreferences = getSharedPreferences("PlantDoctor", Context.MODE_PRIVATE)
        val token = sharedPreferences.getString("token", null) ?: return
        val apiService = PlantApiService.create(token)

        apiService.getAllHistory().enqueue(object : Callback<HistoryResponse> {
            override fun onResponse(call: Call<HistoryResponse>, response: Response<HistoryResponse>) {
                if (response.isSuccessful && response.body()?.status == "success") {
                    response.body()?.let { updateLists(it.data) }
                }
            }
            override fun onFailure(call: Call<HistoryResponse>, t: Throwable) {
                Toast.makeText(this@HistoryListActivity, "網路連線失敗", Toast.LENGTH_SHORT).show()
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
}

// --- 現代化 Material 3 Adapter 實作 ---

class HistoryAdapter(
    private val historyList: List<HistoryItem>,
    private val launcher: androidx.activity.result.ActivityResultLauncher<Intent>
) : RecyclerView.Adapter<HistoryAdapter.HistoryViewHolder>() {

    class HistoryViewHolder(view: View) : RecyclerView.ViewHolder(view) {
        val tvName: TextView = view.findViewById(R.id.tv_history_name)
        val tvDate: TextView = view.findViewById(R.id.tv_history_date)
        val tvStatus: TextView = view.findViewById(R.id.tv_history_status)
        val tvStatusBadge: TextView = view.findViewById(R.id.tv_status_badge)
        val tvSafetyBadge: TextView = view.findViewById(R.id.tv_safety_badge)
        val imgHistory: ImageView = view.findViewById(R.id.img_history_plant)
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): HistoryViewHolder {
        val view = LayoutInflater.from(parent.context).inflate(R.layout.item_history, parent, false)
        return HistoryViewHolder(view)
    }

    override fun onBindViewHolder(holder: HistoryViewHolder, position: Int) {
        val item = historyList[position]
        val tagSuffix = if (!item.plant_tag.isNullOrBlank()) " [${item.plant_tag}]" else ""
        holder.tvName.text = "${item.crop_name ?: "未知植物"}$tagSuffix"
        holder.tvDate.text = "📅 ${item.created_at}"

        val effectiveStatus = if (!item.user_corrected_status.isNullOrBlank()) {
            item.user_corrected_status
        } else {
            item.status_name ?: "無法判定"
        }

        // 1. 狀態膠囊徽章 (健康=綠色，病害=紅色)
        val isHealthy = effectiveStatus.contains("健康")
        if (isHealthy) {
            val confText = item.confidence?.let { String.format(Locale.getDefault(), " %.0f%%", it * 100) } ?: ""
            holder.tvStatusBadge.text = "🌿 健康$confText"
            holder.tvStatusBadge.setBackgroundResource(R.drawable.bg_badge_healthy)
            holder.tvStatusBadge.setTextColor(Color.parseColor("#2E7D32"))
        } else {
            val confText = item.confidence?.let { String.format(Locale.getDefault(), " %.0f%%", it * 100) } ?: ""
            holder.tvStatusBadge.text = "⚠️ $effectiveStatus$confText"
            holder.tvStatusBadge.setBackgroundResource(R.drawable.bg_badge_disease)
            holder.tvStatusBadge.setTextColor(Color.parseColor("#C62828"))
        }

        // 2. 室內與寵物友善標章
        holder.tvSafetyBadge.text = "🐾 寵物安全"
        holder.tvSafetyBadge.setBackgroundResource(R.drawable.bg_badge_safe)

        // 3. 診斷摘要說明 (拍立得卡片精簡排版)
        holder.tvStatus.text = buildString {
            if (!item.user_corrected_status.isNullOrBlank()) {
                append(item.user_corrected_status)
            } else {
                append(item.status_name ?: "無法判定")
            }
        }

        // 4. 圓角縮圖載入
        val finalUrl = fixImageUrl(item.image_url)
        Glide.with(holder.itemView.context)
            .load(finalUrl)
            .placeholder(android.R.drawable.ic_menu_gallery)
            .error(android.R.drawable.ic_dialog_alert)
            .into(holder.imgHistory)

        // 5. 點擊整張質感卡片跳轉詳情頁
        holder.itemView.setOnClickListener {
            SoundManager.playBubblePop()
            val intent = Intent(holder.itemView.context, HistoryDetailActivity::class.java).apply {
                putExtra("DIARY_ID", item.id)
            }
            launcher.launch(intent)
        }
    }

    override fun getItemCount() = historyList.size

    private fun fixImageUrl(rawUrl: String): String {
        if (rawUrl.startsWith("content://") || rawUrl.startsWith("file://")) {
            return rawUrl
        }

        val resolvedIp = com.example.plantdoctor.PlantApiService.currentRunningIp
        val isCloud = resolvedIp.contains("railway.app")
        val schemeAndHost = when {
            isCloud -> "https://$resolvedIp"
            resolvedIp.startsWith("http://") || resolvedIp.startsWith("https://") -> resolvedIp.trimEnd('/')
            else -> "http://$resolvedIp:8000"
        }

        var url = rawUrl
            .replace("http://127.0.0.1:8000", schemeAndHost)
            .replace("http://localhost:8000", schemeAndHost)
            .replace("127.0.0.1", resolvedIp)
            .replace("localhost", resolvedIp)

        if (!url.startsWith("http://") && !url.startsWith("https://")) {
            val safePath = if (url.startsWith("/")) url else "/$url"
            url = "$schemeAndHost$safePath"
        }

        val keywordStatic = "static/"
        if (url.contains(keywordStatic)) {
            val startIndex = url.indexOf(keywordStatic)
            url = "$schemeAndHost/$keywordStatic" + url.substring(startIndex + keywordStatic.length)
        }

        val keywordUploads = "uploads/"
        if (url.contains(keywordUploads)) {
            val startIndex = url.indexOf(keywordUploads)
            url = "$schemeAndHost/$keywordUploads" + url.substring(startIndex + keywordUploads.length)
        }

        return url
    }
}
