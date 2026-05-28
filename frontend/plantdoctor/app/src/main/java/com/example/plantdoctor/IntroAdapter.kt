package com.example.plantdoctor

import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.ImageView
import android.widget.TextView
import androidx.recyclerview.widget.RecyclerView

class IntroAdapter : RecyclerView.Adapter<IntroAdapter.IntroViewHolder>() {

    // 1. 定義四頁的圖片資源
    private val images = listOf(
        R.drawable.img_intro_upload,   // 第一頁：上傳照片
        R.drawable.img_intro_diagnose, // 第二頁：AI診斷中
        R.drawable.img_intro_result,   // 第三頁：診斷報告
        R.drawable.img_intro_store    // 第四頁：🌟 紀錄筆記與儲存（這裡先沿用第三頁的圖，你可以換成專屬圖）
    )

    // 2. 定義四頁對應的溫暖介紹文字
    private val titles = listOf(
        "上傳植物照片",
        "讓AI醫生診斷植物狀態",
        "為您的植物生成照顧方案",
        "填寫觀察筆記並儲存病例" // 🌟 新增第四頁溫暖文字
    )

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): IntroViewHolder {
        val view = LayoutInflater.from(parent.context).inflate(R.layout.item_intro_page, parent, false)
        return IntroViewHolder(view)
    }

    override fun onBindViewHolder(holder: IntroViewHolder, position: Int) {
        holder.imgIntro.setImageResource(images[position])
        holder.txtIntroTitle.text = titles[position]
    }

    // 🌟 總頁數直接回傳 images.size（也就是 4 頁）
    override fun getItemCount(): Int = images.size

    class IntroViewHolder(itemView: View) : RecyclerView.ViewHolder(itemView) {
        val imgIntro: ImageView = itemView.findViewById(R.id.img_intro)
        val txtIntroTitle: TextView = itemView.findViewById(R.id.txt_intro_title)
    }
}