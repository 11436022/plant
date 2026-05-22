package com.example.plantdoctor

import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.view.ViewGroup
import android.widget.FrameLayout
import android.widget.ImageButton
import android.widget.ImageView
import androidx.appcompat.app.AppCompatActivity
import com.bumptech.glide.Glide
import com.github.chrisbanes.photoview.PhotoView

class ImagePreviewActivity : AppCompatActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // 1. 建立最底層的容器 (FrameLayout) 用來疊加元件
        val rootLayout = FrameLayout(this).apply {
            layoutParams = ViewGroup.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.MATCH_PARENT
            )
            setBackgroundColor(android.graphics.Color.BLACK) // 質感黑背景
        }

        // 2. 建立 PhotoView（負責雙指無限制缩放、單指平移）
        val photoView = PhotoView(this).apply {
            layoutParams = FrameLayout.LayoutParams(
                FrameLayout.LayoutParams.MATCH_PARENT,
                FrameLayout.LayoutParams.MATCH_PARENT
            )
            scaleType = ImageView.ScaleType.FIT_CENTER
        }
        rootLayout.addView(photoView) // 把圖片元件塞進容器

        // 3. 建立左上角返回箭頭（完全對齊組員的規格，顏色優化為白色）
        val btnBack = ImageButton(this).apply {
            // 設定跟組員一模一樣的 48dp 大小
            val density = resources.displayMetrics.density
            val size = (48 * density).toInt()
            val startMargin = (16 * density).toInt()
            val topMargin = (72 * density).toInt() // 維持原汁原味的 72dp 頂部距離

            layoutParams = FrameLayout.LayoutParams(size, size).apply {
                setMargins(startMargin, topMargin, 0, 0)
            }

            // 外觀與資源設定
            setBackgroundResource(R.drawable.ic_back) // 直接取用專案裡的 ic_back
            backgroundTintList = android.content.res.ColorStateList.valueOf(android.graphics.Color.WHITE) // 🌟 改為白色，黑底才看得到
            contentDescription = "返回診斷報告"

            // 點擊事件：按下去就清脆一聲泡泡音，直接返回報告頁面！
            setOnClickListener {
                SoundManager.playBubblePop()
                finish()
            }
        }
        rootLayout.addView(btnBack) // 把返回按鈕疊在圖片上方

        // 設定主畫面為這個複合容器
        setContentView(rootLayout)

        // 4. 接收上一頁傳過來的圖片路徑並載入
        val imagePath = intent.getStringExtra("IMAGE_PATH")
        if (!imagePath.isNullOrEmpty()) {
            Glide.with(this)
                .load(Uri.parse(imagePath))
                .into(photoView)
        }
    }
}