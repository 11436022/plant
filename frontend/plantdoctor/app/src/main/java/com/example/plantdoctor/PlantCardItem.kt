package com.example.plantdoctor

import java.io.File

data class PlantCardItem(
    val plantIndex: Int,              // 第幾株植物 (1, 2, 3...)
    var name: String,                 // 植物名稱 (例如: "植物 01")
    var isAnalyzing: Boolean = false, // 獨立轉圈 Loading 狀態
    var lastDiagnosis: String? = null,// 最新診斷結果 (例如: "健康", "褐斑病")
    var lastConfidence: Double? = null,// 信心度
    var lastCapturedTime: String? = null, // 🌟 補上這行即可修復！
    var capturedImageFile: File? = null // 最新拍攝的圖片檔案
)