package com.example.plantdoctor

import android.content.Context
import android.content.res.ColorStateList
import android.graphics.Color
import android.view.View
import android.widget.Button
import android.widget.ImageButton
import android.widget.TextView
import androidx.cardview.widget.CardView

object ThemeManager {

    fun applyTheme(
        context: Context,
        rootLayout: View?,
        titles: List<TextView> = emptyList(),
        mainButtons: List<Button> = emptyList(),
        imageButtons: List<ImageButton> = emptyList()
    ) {
        val sharedPref = context.getSharedPreferences("PlantDoctor", Context.MODE_PRIVATE)
        val themeId = sharedPref.getInt("THEME_COLOR_ID", 0) // 0:綠, 1:藍, 2:棕, 3:粉

        val bgResource: Int
        val titleColorStr: String
        val mainColorStr: String

        when (themeId) {
            1 -> { // 🌌 海洋藍
                bgResource = R.drawable.gradient_blue
                titleColorStr = "#0D47A1"
                mainColorStr = "#1565C0"
            }
            2 -> { // 🪵 暖陽橙 (棕)
                bgResource = R.drawable.gradient_brown
                titleColorStr = "#5D4037"
                mainColorStr = "#D84315"
            }
            3 -> { // 🌸 蜜桃粉
                bgResource = R.drawable.gradient_pink
                titleColorStr = "#880E4F"
                mainColorStr = "#AD1457"
            }
            else -> { // 🌿 經典陽光綠
                bgResource = R.drawable.gradient_green
                titleColorStr = "#1B5E20"
                mainColorStr = "#2E7D32"
            }
        }

        val titleColor = Color.parseColor(titleColorStr)
        val mainColor = Color.parseColor(mainColorStr)
        val colorStateList = ColorStateList.valueOf(mainColor)

        rootLayout?.setBackgroundResource(bgResource)
        titles.forEach { it.setTextColor(titleColor) }
        mainButtons.forEach { it.backgroundTintList = colorStateList }
        imageButtons.forEach { it.imageTintList = colorStateList }
    }

    /**
     * 🌟 全新擴充：專屬於未儲存對話框（Dialog）的風格換色大總管
     * 讓對話框不採用突兀的漸層圖，而是改用各主題對應的質感純色背景與高對比文字！
     */
    fun applyThemeToDialog(
        context: Context,
        cardRoot: CardView,
        btnClose: ImageButton,
        tvTitle: TextView,
        tvMessage: TextView
    ) {
        val sharedPref = context.getSharedPreferences("PlantDoctor", Context.MODE_PRIVATE)
        val themeId = sharedPref.getInt("THEME_COLOR_ID", 0)

        val dialogBgColorStr: String    // 對話框卡片底色
        val titleColorStr: String       // 標題顏色
        val messageColorStr: String     // 內容文字與叉叉顏色

        when (themeId) {
            1 -> { // 🌌 海洋藍風格：採用高質感深藍底配白字
                dialogBgColorStr = "#1A237E"
                titleColorStr = "#9FA8DA"
                messageColorStr = "#FFFFFF"
            }
            2 -> { // 🪵 暖陽棕風格：採用暖調深可可底配米白字
                dialogBgColorStr = "#3E2723"
                titleColorStr = "#FFCC80"
                messageColorStr = "#FFFFFF"
            }
            3 -> { // 🌸 蜜桃粉風格：採用浪漫深莓紅底配淺粉字
                dialogBgColorStr = "#4A0033"
                titleColorStr = "#F48FB1"
                messageColorStr = "#FFFFFF"
            }
            else -> { // 🌿 經典陽光綠風格：清爽舒適的亮白底配森林綠字
                dialogBgColorStr = "#FFFFFF"
                titleColorStr = "#1B5E20"
                messageColorStr = "#555555"
            }
        }

        // 解析顏色
        val bgColor = Color.parseColor(dialogBgColorStr)
        val titleColor = Color.parseColor(titleColorStr)
        val msgColor = Color.parseColor(messageColorStr)

        // 🌟 透過 KT 強制注入顏色，完全不受手機系統干擾！
        cardRoot.setCardBackgroundColor(bgColor)
        tvTitle.setTextColor(titleColor)
        tvMessage.setTextColor(msgColor)
        btnClose.imageTintList = ColorStateList.valueOf(titleColor) // 叉叉顏色與標題同步
    }
}