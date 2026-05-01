package com.example.plantdoctor

import android.content.Context
import android.content.Intent
import android.os.Bundle
import android.util.Log
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.ImageButton
import android.widget.ImageView
import android.widget.LinearLayout
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.bumptech.glide.Glide
import retrofit2.Call
import retrofit2.Callback
import retrofit2.Response

data class HistoryItem(
    val id: Int,
    val crop_name: String,
    val created_at: String,
    val status_name: String,
    val image_url: String,
    var suggestion: String? = null,
    var treatment: String? = null,
    var isExpanded: Boolean = false
)

class HistoryListActivity : AppCompatActivity() {
    private lateinit var adapter: HistoryAdapter
    private val historyList = mutableListOf<HistoryItem>()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_history_list)

        // 處理返回按鈕邏輯
        val btnBackHome = findViewById<ImageButton>(R.id.btn_back_home)
        btnBackHome.setOnClickListener {
            finish()
        }

        val rvHistory = findViewById<RecyclerView>(R.id.rv_history_list)
        rvHistory.layoutManager = LinearLayoutManager(this)

        adapter = HistoryAdapter(historyList)
        rvHistory.adapter = adapter
        fetchHistoryFromServer()
    }

    private fun fetchHistoryFromServer(){
        val sharedPreferences = getSharedPreferences("PlantDoctor", Context.MODE_PRIVATE)
        val token = sharedPreferences.getString("token", null)

        if(token == null){
            val intent = Intent(this, LoginActivity::class.java)
            startActivity(intent)
            finish()
            return
        }

        val apiService = PlantApiService.create()

        apiService.getAllHistory(token).enqueue(object: Callback<HistoryResponse>{
            override fun onResponse(call: Call<HistoryResponse>, response: Response<HistoryResponse>){
                if(response.isSuccessful){
                    val historyResponse = response.body()
                    if(historyResponse != null && historyResponse.status == "success"){
                        historyList.clear()
                        historyList.addAll(historyResponse.data)
                        adapter.notifyDataSetChanged()
                    }
                    else{
                        when (response.code()){
                            401 -> {
                                Toast.makeText(this@HistoryListActivity, "登入已過期，請重新登入", Toast.LENGTH_SHORT).show()
                                val intent = Intent(this@HistoryListActivity, LoginActivity::class.java)
                                startActivity(intent)
                                finish()
                            }
                            404 -> {
                                Toast.makeText(this@HistoryListActivity, "找不到紀錄", Toast.LENGTH_SHORT).show()
                            }
                            else -> {
                                Toast.makeText(this@HistoryListActivity, "伺服器錯誤: ${response.code()}", Toast.LENGTH_SHORT).show()
                            }
                        }
                    }
                }
            }
            override fun onFailure(call: Call<HistoryResponse>, t: Throwable){
                Log.e("API_ERROR", "網路連線失敗: ${t.message}")
                Toast.makeText(this@HistoryListActivity, "網路連線異常，請檢查網路設定", Toast.LENGTH_LONG).show()
            }
        })
    }
}

class HistoryAdapter(private val historyList: List<HistoryItem>) :
    RecyclerView.Adapter<HistoryAdapter.HistoryViewHolder>() {

    class HistoryViewHolder(view: View) : RecyclerView.ViewHolder(view) {
        val tvName: TextView = view.findViewById(R.id.tv_history_name)
        val tvDate: TextView = view.findViewById(R.id.tv_history_date)
        val tvStatus: TextView = view.findViewById(R.id.tv_history_status)
        val tvAdvice: TextView = view.findViewById(R.id.tv_history_advice)
        val layoutDetail: LinearLayout = view.findViewById(R.id.layout_detail)
        val imgArrow: ImageView = view.findViewById(R.id.img_arrow)

        val imgHistory: ImageView = view.findViewById(R.id.img_history_plant)
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

        // --- 修正版：處理本機測試網址與 C 槽路徑錯誤 ---
        var finalImageUrl = item.image_url
            .replace("127.0.0.1", "10.0.2.2")
            .replace("localhost", "10.0.2.2")

        // 魔法切除：把後端傳錯的 C 槽絕對路徑砍掉
        if (finalImageUrl.contains("C:/Users/LL/Documents/MyProjects/plant/")) {
            finalImageUrl = finalImageUrl.replace("C:/Users/LL/Documents/MyProjects/plant/", "")
        }

        // 驗證我們有沒有切對
        Log.d("Glide_Check", "最終修復圖片網址: $finalImageUrl")

        Glide.with(holder.itemView.context)
            .load(finalImageUrl)
            .placeholder(android.R.drawable.ic_menu_gallery)
            .error(android.R.drawable.ic_dialog_alert)
            .into(holder.imgHistory)
        // ----------------------------------------

        val detailText = if (item.suggestion != null) {
            "【建議】\n${item.suggestion}\n\n【處理】\n${item.treatment}"
        } else {
            "載入中，請稍候..."
        }
        holder.tvAdvice.text = detailText

        holder.layoutDetail.visibility = if (item.isExpanded) View.VISIBLE else View.GONE
        holder.imgArrow.rotation = if (item.isExpanded) 180f else 0f

        holder.itemView.setOnClickListener {
            val currentPos = holder.adapterPosition
            if (currentPos == RecyclerView.NO_POSITION) return@setOnClickListener

            if (!item.isExpanded) {
                if (item.suggestion == null) {
                    val sharedPref = holder.itemView.context.getSharedPreferences("PlantDoctor", Context.MODE_PRIVATE)
                    val token = sharedPref.getString("token", "") ?: ""

                    PlantApiService.create().getDiaryDetail(item.id, token).enqueue(object : Callback<DetailDetailResponse> {
                        override fun onResponse(call: Call<DetailDetailResponse>, response: Response<DetailDetailResponse>) {
                            if (response.isSuccessful) {
                                val detail = response.body()?.data
                                item.suggestion = detail?.suggestion
                                item.treatment = detail?.treatment
                                item.isExpanded = true
                                notifyItemChanged(currentPos)
                            }
                        }
                        override fun onFailure(call: Call<DetailDetailResponse>, t: Throwable) {
                            Toast.makeText(holder.itemView.context, "讀取失敗", Toast.LENGTH_SHORT).show()
                        }
                    })
                } else {
                    item.isExpanded = true
                    notifyItemChanged(currentPos)
                }
            } else {
                item.isExpanded = false
                notifyItemChanged(currentPos)
            }
        }
    }

    override fun getItemCount() = historyList.size
}