package com.example.plantdoctor

import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Button
import android.widget.ProgressBar
import android.widget.TextView
import androidx.recyclerview.widget.RecyclerView

class PlantAdapter(
    private val plantList: MutableList<PlantCardItem>,
    private val onAnalyzeClick: (plant: PlantCardItem, position: Int) -> Unit
) : RecyclerView.Adapter<PlantAdapter.PlantViewHolder>() {

    class PlantViewHolder(itemView: View) : RecyclerView.ViewHolder(itemView) {
        val tvPlantTitle: TextView = itemView.findViewById(R.id.tvPlantTitle)
        val tvDiagnosisResult: TextView = itemView.findViewById(R.id.tvDiagnosisResult)
        val btnAnalyze: Button = itemView.findViewById(R.id.btnAnalyze)
        val progressBar: ProgressBar = itemView.findViewById(R.id.progressBar)
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): PlantViewHolder {
        val view = LayoutInflater.from(parent.context)
            .inflate(R.layout.item_plant_card, parent, false)
        return PlantViewHolder(view)
    }

    override fun onBindViewHolder(holder: PlantViewHolder, position: Int) {
        val item = plantList[position]

        holder.tvPlantTitle.text = item.name

        // 1. 處理診斷結果文字
        if (item.lastDiagnosis != null) {
            val confText = item.lastConfidence?.let { " (${(it * 100).toInt()}%)" } ?: ""
            holder.tvDiagnosisResult.text = "最新狀態: ${item.lastDiagnosis}$confText"
        } else {
            holder.tvDiagnosisResult.text = "尚未進行檢測"
        }

        // 2. 獨立處理這張卡片的 Loading 轉圈狀態
        if (item.isAnalyzing) {
            holder.progressBar.visibility = View.VISIBLE
            holder.btnAnalyze.isEnabled = false
            holder.btnAnalyze.text = "分析中..."
        } else {
            holder.progressBar.visibility = View.GONE
            holder.btnAnalyze.isEnabled = true
            holder.btnAnalyze.text = "📷 拍攝/檢測"
        }

        // 3. 點擊按鈕，觸發檢測 Callback
        holder.btnAnalyze.setOnClickListener {
            onAnalyzeClick(item, position)
        }
    }

    override fun getItemCount(): Int = plantList.size

    // 更新特定卡片狀態
    fun updateItem(position: Int) {
        notifyItemChanged(position)
    }
}