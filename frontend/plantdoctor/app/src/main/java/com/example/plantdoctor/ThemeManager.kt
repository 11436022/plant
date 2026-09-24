package com.example.plantdoctor

import android.content.Context
import android.content.res.ColorStateList
import android.graphics.Color
import android.graphics.drawable.GradientDrawable
import android.view.View
import android.widget.Button
import android.widget.EditText
import android.widget.ImageButton
import android.widget.RadioButton
import android.widget.SeekBar
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
     * 🌟 WebcamActivity 專用動態主題套用
     */
    fun applyThemeToWebcam(
        context: Context,
        btnSelectSession: TextView?,
        rbSingleMode: RadioButton?,
        rbMultiMode: RadioButton?,
        seekBar: SeekBar?,
        etInterval: EditText?,
        panelBackground: View?
    ) {
        val sharedPref = context.getSharedPreferences("PlantDoctor", Context.MODE_PRIVATE)
        val themeId = sharedPref.getInt("THEME_COLOR_ID", 0)

        val mainColorStr: String
        val secondaryBgStr: String

        when (themeId) {
            1 -> { // 🌌 海洋藍
                mainColorStr = "#1565C0"
                secondaryBgStr = "#E8EAF6"
            }
            2 -> { // 🪵 暖陽橙 (棕)
                mainColorStr = "#D84315"
                secondaryBgStr = "#FBE9E7"
            }
            3 -> { // 🌸 蜜桃粉
                mainColorStr = "#AD1457"
                secondaryBgStr = "#FCE4EC"
            }
            else -> { // 🌿 經典陽光綠
                mainColorStr = "#2E7D32"
                secondaryBgStr = "#E8F5E9"
            }
        }

        val mainColor = Color.parseColor(mainColorStr)
        val secondaryColor = Color.parseColor(secondaryBgStr)

        // 1. 組別選取按鈕 (btnSelectSession) 顏色與樣式動態設定
        btnSelectSession?.apply {
            setTextColor(mainColor)
            background = null // 移除任何背景邊框框線
            setPadding(0, 0, 0, 0)
        }

        // 2. RadioButton 與 SeekBar 顏色連動
        val colorStateList = ColorStateList.valueOf(mainColor)
        rbSingleMode?.buttonTintList = colorStateList
        rbMultiMode?.buttonTintList = colorStateList
        seekBar?.thumbTintList = colorStateList
        seekBar?.progressTintList = colorStateList

        // 3. 下方半透明面板動態圓角與邊框
        panelBackground?.apply {
            val panelDrawable = GradientDrawable().apply {
                setColor(Color.parseColor("#CC111111")) // 80% 半透明深灰
                setStroke(2, mainColor)
                cornerRadius = 24f
            }
            background = panelDrawable
        }
    }

    fun applyThemeToDialog(
        context: Context,
        cardRoot: CardView,
        btnClose: ImageButton,
        tvTitle: TextView,
        tvMessage: TextView
    ) {
        val sharedPref = context.getSharedPreferences("PlantDoctor", Context.MODE_PRIVATE)
        val themeId = sharedPref.getInt("THEME_COLOR_ID", 0)

        val dialogBgColorStr: String
        val titleColorStr: String
        val messageColorStr: String

        when (themeId) {
            1 -> {
                dialogBgColorStr = "#1A237E"
                titleColorStr = "#9FA8DA"
                messageColorStr = "#FFFFFF"
            }
            2 -> {
                dialogBgColorStr = "#3E2723"
                titleColorStr = "#FFCC80"
                messageColorStr = "#FFFFFF"
            }
            3 -> {
                dialogBgColorStr = "#4A0033"
                titleColorStr = "#F48FB1"
                messageColorStr = "#FFFFFF"
            }
            else -> {
                dialogBgColorStr = "#FFFFFF"
                titleColorStr = "#1B5E20"
                messageColorStr = "#555555"
            }
        }

        val bgColor = Color.parseColor(dialogBgColorStr)
        val titleColor = Color.parseColor(titleColorStr)
        val msgColor = Color.parseColor(messageColorStr)

        cardRoot.setCardBackgroundColor(bgColor)
        tvTitle.setTextColor(titleColor)
        tvMessage.setTextColor(msgColor)
        btnClose.imageTintList = ColorStateList.valueOf(titleColor)
    }
}