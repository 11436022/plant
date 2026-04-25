package com.example.plantdoctor

import android.content.Intent
import android.os.Bundle
import android.transition.TransitionManager
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
import android.content.Context
import android.util.Log
import retrofit2.Call
import retrofit2.Callback
import retrofit2.Response



data class HistoryItem(
    val id: Int,              
    val crop_name: String,    
    val created_at: String,         
    val status_name: String,      
    val image_url: String,     
    var suggestion: String? = null, // 一開始是空的，點擊後才抓
    var treatment: String? = null,  // 一開始是空的
    var isExpanded: Boolean = false
)


class HistoryListActivity : AppCompatActivity() {
    private lateinit var adapter: HistoryAdapter
    private val historyList = mutableListOf<HistoryItem>()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_history_list)

        val rvHistory = findViewById<RecyclerView>(R.id.rv_history_list)
        rvHistory.layoutManager = LinearLayoutManager(this)

        adapter = HistoryAdapter(historyList)
        rvHistory.adapter = adapter
        fetchHistoryFromServer()
    }
    private fun fetchHistoryFromServer(){
        // 1. 取得存好的 Token
        val sharedPreferences = getSharedPreferences("PlantDoctor", Context.MODE_PRIVATE)
        val token = sharedPreferences.getString("token", null)

        if(token == null){
            val intent = Intent(this, LoginActivity::class.java)
            startActivity(intent)
            finish()
            return
        }
        // 2. 建立 API 連線
        val apiService = PlantApiService.create()

        // 3. 呼叫 getAllHistory
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
                // --- 處理網路連線失敗  ---
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

        // 2. 詳情資料賦值 (處理 null 的情況)
        // 將建議與處理方法組合在一起顯示
        val detailText = if (item.suggestion != null) {
            "【建議】\n${item.suggestion}\n\n【處理】\n${item.treatment}"
        } else {
            "載入中，請稍候..." 
        }
        holder.tvAdvice.text = detailText

        // 根據狀態顯示或隱藏細節區域
        holder.layoutDetail.visibility = if (item.isExpanded) View.VISIBLE else View.GONE

        // 旋轉箭頭圖示 (展開時向上，縮起時向下)
        holder.imgArrow.rotation = if (item.isExpanded) 180f else 0f

        holder.itemView.setOnClickListener {
            if (!item.isExpanded) {
                // 如果還沒抓過詳情 (判斷 suggestion 是否為空)
                if (item.suggestion == null) {
                    val sharedPref = holder.itemView.context.getSharedPreferences("PlantDoctor", Context.MODE_PRIVATE)
                    val token = sharedPref.getString("token", "") ?: ""
                    
                    PlantApiService.create().getDiaryDetail(item.id, token).enqueue(object : Callback<DetailDetailResponse> {
                        override fun onResponse(call: Call<DetailDetailResponse>, response: Response<DetailDetailResponse>) {
                            if (response.isSuccessful) {
                                val detail = response.body()?.data
                                // 把抓到的詳情補回這個 item
                                item.suggestion = detail?.suggestion
                                item.treatment = detail?.treatment
                                
                                // 展開並更新
                                item.isExpanded = true
                                val currentPos = holder.adapterPosition
                                if (currentPos != RecyclerView.NO_POSITION) {
                                    notifyItemChanged(currentPos)
                                }
                            }
                        }
                        override fun onFailure(call: Call<DetailDetailResponse>, t: Throwable) {
                            Toast.makeText(holder.itemView.context, "讀取失敗", Toast.LENGTH_SHORT).show()
                        }
                    })
                } else {
                    // 已經有資料了，直接展開
                    item.isExpanded = true
                    notifyItemChanged(position)
                }
            }
             else {
                // 縮起來
                item.isExpanded = false
                notifyItemChanged(position)
            }
        }
    }

    override fun getItemCount() = historyList.size
}