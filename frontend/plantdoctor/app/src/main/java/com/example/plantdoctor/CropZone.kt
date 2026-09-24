package com.example.plantdoctor

import android.graphics.RectF

/**
 * 選取框區域資料模型 (ROI Data Model)
 *
 * @param id 區域識別碼 (如 1 代表 plant01)
 * @param name 自訂植物或區域名稱 (如 "1號龜背芋")
 * @param rectNorm 歸一化比例座標 (0.0f ~ 1.0f)，確保不同螢幕與解析度下位置精準
 * @param intervalMinutes 定時拍攝間隔 (預設 30 分鐘，單一或多植物可自訂)
 * @param lastShotTimestamp 上次拍攝的時間戳記 (系統毫秒數)
 * @param isEnabled 是否啟用定時自動監控
 */
data class CropZone(
    val id: Int,
    var name: String = "植物 $id",
    var rectNorm: RectF = RectF(0.2f, 0.2f, 0.8f, 0.8f), // 預設中間區域
    var intervalMinutes: Long = 30,
    var lastShotTimestamp: Long = 0,
    var isEnabled: Boolean = true,
    var lastCapturedTime: Long = 0L  // ⭕ 補上這一行：紀錄最後一次拍攝的時間戳記 (解決 2 & 3 報錯)
)