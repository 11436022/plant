package com.example.plantdoctor // 請根據你的專案 package 路徑調整

import java.io.File
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.asRequestBody

object PlantUploadHelper {

    /**
     * 建立帶有自訂檔名規範的 MultipartBody.Part
     *
     * @param username 使用者名稱 (例如: "張小明")
     * @param sessionName 自訂組別名稱 (例如: "客廳植栽")
     * @param plantIndex 第幾株植物 (例如: 1, 2, 3)
     * @param imageFile 準備上傳的照片檔案
     * @return 封裝好自訂檔名的 MultipartBody.Part，可直接傳給 Retrofit
     */
    fun createPlantImagePart(
        username: String,
        sessionName: String,
        plantIndex: Int,
        imageFile: File
    ): MultipartBody.Part {

        // 1. 取得當前時間戳記 (格式: YYYYMMDD_HHMMSS)
        val timeFormatter = SimpleDateFormat("yyyyMMdd_HHmmss", Locale.getDefault())
        val currentTimeStr = timeFormatter.format(Date())

        // 2. 清除字串中的作業系統非法字元 (/ \ : * ? " < > |)，保留中文與底線
        val safeUsername = username.ifBlank { "User" }
            .replace("[\\\\/:*?\"<>|]".toRegex(), "")

        val safeSession = sessionName.ifBlank { "DefaultGroup" }
            .replace("[\\\\/:*?\"<>|]".toRegex(), "")

        // 3. 格式化植物 ID (例如: plant01, plant02...)
        val plantIdStr = String.format(Locale.US, "plant%02d", plantIndex)

        // 4. 組合符合規範的檔案名稱
        // 範例：張小明_客廳植栽_20260725_153000_plant01.jpg
        val customFilename = "${safeUsername}_${safeSession}_${currentTimeStr}_${plantIdStr}.jpg"

        // 5. 將 File 轉為 RequestBody 並打包為 MultipartBody.Part
        val requestFile = imageFile.asRequestBody("image/jpeg".toMediaTypeOrNull())

        // 關鍵：將 customFilename 傳入第三個參數，後端 `file.filename` 就會收到這個名字
        return MultipartBody.Part.createFormData("file", customFilename, requestFile)
    }
}