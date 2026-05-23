package com.example.plantdoctor

import android.content.Context
import android.content.res.ColorStateList
import android.graphics.Color
import android.view.View
import android.widget.Button
import android.widget.ImageButton
import android.widget.TextView

object ThemeManager {

    /**
     * 🌟 全域核心：只要把任何頁面的 rootLayout 傳進來，就能自動幫該頁面換全套背景與元件顏色！
     * @param context 頁面的 Context
     * @param rootLayout 該頁面的最底層 Layout（例如 ConstraintLayout 或 LinearLayout）
     * @param titles 需要同步換色的大標題 TextView 列表（可不傳）
     * @param mainButtons 需要同步換色的主要功能按鈕 Button 列表（可不傳）
     * @param imageButtons 需要同步換色的 ImageButton 箭頭或圖示列表（可不傳）
     */
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

        // 1. 換背景
        rootLayout?.setBackgroundResource(bgResource)

        // 2. 換大字顏色
        titles.forEach { it.setTextColor(titleColor) }

        // 3. 換主按鈕 Tint 顏色
        mainButtons.forEach { it.backgroundTintList = colorStateList }

        // 4. 換返回箭頭或圖示 Tint 顏色
        imageButtons.forEach { it.imageTintList = colorStateList }
    }
}