package com.example.plantdoctor

import android.graphics.Bitmap
import android.graphics.RectF
import com.example.plantdoctor.PlantUploadHelper
import java.io.File
import java.io.FileOutputStream

object CropAndUploadEngine {

    /**
     * 執行特定框框的「裁切 ➔ 打包 ➔ 上傳」
     */
    fun processZoneUpload(
        fullBitmap: Bitmap,
        zone: CropZone,
        username: String,
        sessionName: String,
        cacheDir: File,
        onSuccess: (WebcamAnalyzeResponse) -> Unit,
        onError: (String) -> Unit
    ) {
        // 1. 計算實體像素切片範圍
        val imgWidth = fullBitmap.width
        val imgHeight = fullBitmap.height

        val left = (zone.rectNorm.left * imgWidth).toInt().coerceIn(0, imgWidth - 1)
        val top = (zone.rectNorm.top * imgHeight).toInt().coerceIn(0, imgHeight - 1)
        val right = (zone.rectNorm.right * imgWidth).toInt().coerceIn(left + 1, imgWidth)
        val bottom = (zone.rectNorm.bottom * imgHeight).toInt().coerceIn(top + 1, imgHeight)

        // 2. 無損裁切 Bitmap
        val croppedBitmap = Bitmap.createBitmap(
            fullBitmap, left, top, right - left, bottom - top
        )

        // 3. 儲存為暫存檔
        val cropFile = File(cacheDir, "crop_zone_${zone.id}.jpg")
        FileOutputStream(cropFile).use { out ->
            croppedBitmap.compress(Bitmap.CompressFormat.JPEG, 92, out)
        }

        // 4. 使用我們之前的檔名產生器打檔名 (帶入該框框的 ID 與時間)
        // 檔名範例: 陳小華_客廳溫室_20260725_153800_plant01.jpg
        val imagePart = PlantUploadHelper.createPlantImagePart(
            username = username,
            sessionName = sessionName,
            plantIndex = zone.id,
            imageFile = cropFile
        )

        // 5. 呼叫現有 API 上傳！
        PlantApiService.create().analyzeWebcamFrame(imagePart).enqueue(object : retrofit2.Callback<WebcamAnalyzeResponse> {
            override fun onResponse(
                call: retrofit2.Call<WebcamAnalyzeResponse>,
                response: retrofit2.Response<WebcamAnalyzeResponse>
            ) {
                if (response.isSuccessful && response.body() != null) {
                    onSuccess(response.body()!!)
                } else {
                    onError("HTTP ${response.code()}")
                }
            }

            override fun onFailure(call: retrofit2.Call<WebcamAnalyzeResponse>, t: Throwable) {
                onError(t.message ?: "網絡錯誤")
            }
        })
    }
}