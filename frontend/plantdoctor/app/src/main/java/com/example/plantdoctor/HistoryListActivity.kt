package com.example.plantdoctor

import android.content.Context
import android.content.Intent
import android.os.Bundle
import android.text.Editable
import android.text.TextWatcher
import android.util.Log
import android.view.LayoutInflater
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
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.bumptech.glide.Glide
import com.google.gson.Gson
import com.google.gson.annotations.SerializedName
import com.google.gson.reflect.TypeToken
import retrofit2.Call
import retrofit2.Callback
import retrofit2.Response

// 歷史紀錄資料模型
data class HistoryItem(
    @SerializedName("id") val id: Int,
    @SerializedName("crop_name") val crop_name: String,
    @SerializedName("created_at") val created_at: String,
    @SerializedName("status_name") val status_name: String,
    @SerializedName("image_url") val image_url: String,
    @SerializedName("suggestion") var suggestion: String? = null,
    @SerializedName("treatment") var treatment: String? = null,
    @SerializedName("user_note") val user_note: String?,
    var isExpanded: Boolean = false
)

class HistoryListActivity : AppCompatActivity() {
    private lateinit var adapter: HistoryAdapter
    private val displayList = mutableListOf<HistoryItem>()
    private val fullHistoryList = mutableListOf<HistoryItem>()
    private var lastQuery: String = "" // 儲存最後一次搜尋關鍵字

    // 【關鍵修復】註冊一個 ActivityResultLauncher 來處理從詳情頁返回的結果
    private val detailActivityLauncher = registerForActivityResult(ActivityResultContracts.StartActivityForResult()) { result ->
        // 如果結果是 OK (表示在詳情頁有執行刪除成功等操作)
        if (result.resultCode == RESULT_OK) {
            // 就重新從伺服器抓取最新資料
            fetchHistoryFromServer()
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_history_list)

        // 1. 返回按鈕
        findViewById<ImageButton>(R.id.btn_back_home).setOnClickListener { finish() }

        // 2. 搜尋框邏輯
        val etSearch = findViewById<EditText>(R.id.et_search)
        etSearch.addTextChangedListener(object : TextWatcher {
            override fun afterTextChanged(s: Editable?) {
                lastQuery = s.toString()
                filterList(lastQuery)
            }
            override fun beforeTextChanged(s: CharSequence?, start: Int, count: Int, after: Int) {}
            override fun onTextChanged(s: CharSequence?, start: Int, before: Int, count: Int) {}
        })

        // 3. 初始化 RecyclerView
        val rvHistory = findViewById<RecyclerView>(R.id.rv_history_list)
        rvHistory.layoutManager = LinearLayoutManager(this)
        adapter = HistoryAdapter(displayList, detailActivityLauncher)
        rvHistory.adapter = adapter
    }

    // --- 核心改動：當從詳情頁返回時觸發自動更新 ---
    override fun onResume() {
        super.onResume()
        // 每次回到頁面都抓取最新資料，確保刪除後的資料不會留在畫面上
        fetchHistoryFromServer()
    }

    private fun filterList(query: String) {
        val filtered = if (query.isEmpty()) {
            fullHistoryList
        } else {
            fullHistoryList.filter {
                it.crop_name.contains(query, ignoreCase = true) ||
                        it.status_name.contains(query, ignoreCase = true)
            }
        }
        displayList.clear()
        displayList.addAll(filtered)
        adapter.notifyDataSetChanged()
    }

    private fun updateLists(newData: List<HistoryItem>) {
        fullHistoryList.clear()
        fullHistoryList.addAll(newData)
        // 更新時套用最後一次搜尋，避免列表突然重置
        filterList(lastQuery)
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
}

// --- Adapter 實作 ---

class HistoryAdapter(
    private val historyList: List<HistoryItem>,
    private val launcher: androidx.activity.result.ActivityResultLauncher<Intent>
) : RecyclerView.Adapter<HistoryAdapter.HistoryViewHolder>() {

    class HistoryViewHolder(view: View) : RecyclerView.ViewHolder(view) {
        val tvName: TextView = view.findViewById(R.id.tv_history_name)
        val tvDate: TextView = view.findViewById(R.id.tv_history_date)
        val tvStatus: TextView = view.findViewById(R.id.tv_history_status)
        val tvAdvice: TextView = view.findViewById(R.id.tv_history_advice)
        val layoutDetail: LinearLayout = view.findViewById(R.id.layout_detail)
        val imgArrow: ImageView = view.findViewById(R.id.img_arrow)
        val imgHistory: ImageView = view.findViewById(R.id.img_history_plant)
        val btnGoDetail: Button = view.findViewById(R.id.btn_go_detail)
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): HistoryViewHolder {
        val view = LayoutInflater.from(parent.context).inflate(R.layout.item_history, parent, false)
        return HistoryViewHolder(view)
    }

    override fun onBindViewHolder(holder: HistoryViewHolder, position: Int) {
        val item = historyList[position]
        holder.tvName.text = item.crop_name
        holder.tvDate.text = item.created_at
        holder.tvStatus.text = item.status_name

        // 使用路徑修復邏輯
        val finalUrl = fixImageUrl(item.image_url)

        Glide.with(holder.itemView.context)
            .load(finalUrl)
            .placeholder(android.R.drawable.ic_menu_gallery)
            .error(android.R.drawable.ic_dialog_alert)
            .into(holder.imgHistory)

        holder.tvAdvice.text = "點擊查看完整報告" // 簡化提示文字

        // 隱藏不再需要的展開式佈局和箭頭
        holder.layoutDetail.visibility = View.GONE
        holder.imgArrow.visibility = View.GONE
        holder.btnGoDetail.visibility = View.GONE

        // 【新邏輯】點擊整個項目，直接跳轉到詳情頁
        holder.itemView.setOnClickListener {
            val intent = Intent(holder.itemView.context, HistoryDetailActivity::class.java).apply {
                // 將被點擊項目的 ID 傳遞給詳情頁
                putExtra("DIARY_ID", item.id)
            }
            // 使用您已經建立好的 launcher 來啟動 Activity
            launcher.launch(intent)
        }
    }

    override fun getItemCount() = historyList.size

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