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
import androidx.appcompat.app.AppCompatActivity
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView

data class HistoryItem(
    val plantName: String,
    val date: String,
    val status: String,
    val advice: String,
    var isExpanded: Boolean = false // 新增狀態：標記目前是否展開
)

class HistoryListActivity : AppCompatActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_history_list)

        val btnBack = findViewById<ImageButton>(R.id.btn_back_home)
        btnBack.setOnClickListener { finish() }

        val fakeData = listOf(
            HistoryItem("龜背竹", "2026-04-12 14:30", "已診斷：黑星病", "1. 移除染病葉片。\n2. 保持通風。\n3. 噴灑殺菌劑。"),
            HistoryItem("虎尾蘭", "2026-04-11 09:15", "健康", "狀況良好，請保持目前的澆水頻率。"),
            HistoryItem("黃金葛", "2026-04-10 18:45", "已診斷：褐斑病", "1. 減少噴霧。\n2. 移至光線充足處。")
        )

        val rvHistory = findViewById<RecyclerView>(R.id.rv_history_list)
        rvHistory.layoutManager = LinearLayoutManager(this)
        rvHistory.adapter = HistoryAdapter(fakeData)
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
        holder.tvName.text = item.plantName
        holder.tvDate.text = item.date
        holder.tvStatus.text = item.status
        holder.tvAdvice.text = item.advice

        // 根據狀態顯示或隱藏細節區域
        holder.layoutDetail.visibility = if (item.isExpanded) View.VISIBLE else View.GONE

        // 旋轉箭頭圖示 (展開時向上，縮起時向下)
        holder.imgArrow.rotation = if (item.isExpanded) 180f else 0f

        holder.itemView.setOnClickListener {
            // 切換狀態
            item.isExpanded = !item.isExpanded

            // 加入平滑動畫
            TransitionManager.beginDelayedTransition(holder.itemView as ViewGroup)

            // 重新整理這一項的顯示
            notifyItemChanged(position)
        }
    }

    override fun getItemCount() = historyList.size
}