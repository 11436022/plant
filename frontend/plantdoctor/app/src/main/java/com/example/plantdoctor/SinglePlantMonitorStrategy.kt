package com.example.plantdoctor

import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.ImageFormat
import android.graphics.Rect
import android.graphics.YuvImage
import android.os.Handler
import android.os.Looper
import android.util.Log
import androidx.camera.core.ImageProxy
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.toRequestBody
import retrofit2.Call
import retrofit2.Callback
import retrofit2.Response
import java.io.ByteArrayOutputStream
import kotlin.math.min

class SinglePlantMonitorStrategy(private val activity: WebcamActivity) {

    private var lastSampleTime = 0L
    private var streakCount = 0
    private var lastDiseaseName = ""

    // 紀錄上次發送「手機系統通知」的時間戳記 (毫秒)
    private var lastAlertTime = 0L
    // 系統通知重複提醒冷卻間隔：1 小時 (3,600,000 毫秒)
    private val alertCooldownMillis = 3_600_000L

    private val mainHandler = Handler(Looper.getMainLooper())

    /**
     * 🌟 處理相機影格抽樣與時間控制 (30秒~600秒)
     */
    fun processFrame(imageProxy: ImageProxy, isMonitoring: Boolean, intervalSeconds: Long) {
        val currentTime = System.currentTimeMillis()
        val intervalMillis = intervalSeconds * 1000

        if (isMonitoring && (currentTime - lastSampleTime >= intervalMillis)) {
            lastSampleTime = currentTime

            // 1. 轉成 NV21 圖像並裁切中心 1:1 正方形
            val compressedJpegBytes = processImageToCompressedBytes(imageProxy)
            imageProxy.close()

            if (compressedJpegBytes != null) {
                // 2. 送出 API 診斷
                sendFrameToApi(compressedJpegBytes)
            }
        } else {
            imageProxy.close()
        }
    }

    /**
     * 🌟 NV21 轉 Bitmap，裁切正中心 1:1 區域 + 80% JPEG 壓縮
     */
    private fun processImageToCompressedBytes(image: ImageProxy): ByteArray? {
        return try {
            val yBuffer = image.planes[0].buffer
            val uBuffer = image.planes[1].buffer
            val vBuffer = image.planes[2].buffer

            val ySize = yBuffer.remaining()
            val uSize = uBuffer.remaining()
            val vSize = vBuffer.remaining()

            val nv21 = ByteArray(ySize + uSize + vSize)
            yBuffer.get(nv21, 0, ySize)
            vBuffer.get(nv21, ySize, vSize)
            uBuffer.get(nv21, ySize + vSize, uSize)

            val yuvImage = YuvImage(nv21, ImageFormat.NV21, image.width, image.height, null)
            val outStream = ByteArrayOutputStream()
            yuvImage.compressToJpeg(Rect(0, 0, image.width, image.height), 100, outStream)

            val rawBytes = outStream.toByteArray()
            val originalBitmap = BitmapFactory.decodeByteArray(rawBytes, 0, rawBytes.size) ?: return null

            // 裁切正中心 1:1 正方形區域
            val cropSize = min(originalBitmap.width, originalBitmap.height)
            val cropX = (originalBitmap.width - cropSize) / 2
            val cropY = (originalBitmap.height - cropSize) / 2

            val croppedBitmap = Bitmap.createBitmap(originalBitmap, cropX, cropY, cropSize, cropSize)
            if (croppedBitmap != originalBitmap) {
                originalBitmap.recycle()
            }

            val finalStream = ByteArrayOutputStream()
            croppedBitmap.compress(Bitmap.CompressFormat.JPEG, 80, finalStream)
            val finalBytes = finalStream.toByteArray()

            croppedBitmap.recycle()
            finalBytes

        } catch (e: Exception) {
            Log.e("SINGLE_STRATEGY", "圖像處理失敗: ${e.message}")
            null
        }
    }

    /**
     * 🌟 上傳至後端 API 診斷
     */
    private fun sendFrameToApi(jpegBytes: ByteArray) {
        val sharedPref = activity.getSharedPreferences("PlantDoctor", android.content.Context.MODE_PRIVATE)
        val token = sharedPref.getString("token", null)

        val requestFile = jpegBytes.toRequestBody("image/jpeg".toMediaTypeOrNull())
        val body = MultipartBody.Part.createFormData("file", "webcam_single.jpg", requestFile)

        val apiService = PlantApiService.create(token)
        apiService.analyzeWebcamFrame(body).enqueue(object : Callback<WebcamAnalyzeResponse> {
            override fun onResponse(
                call: Call<WebcamAnalyzeResponse>,
                response: Response<WebcamAnalyzeResponse>
            ) {
                if (response.isSuccessful) {
                    response.body()?.let { result ->
                        val cropName = result.diagnosis.crop_name ?: ""
                        val statusName = result.diagnosis.status_name ?: "狀態未知"
                        val fullDiseaseName = "$cropName $statusName".trim()

                        handleDiagnosisResult(fullDiseaseName)
                    }
                }
            }

            override fun onFailure(call: Call<WebcamAnalyzeResponse>, t: Throwable) {
                Log.e("SINGLE_STRATEGY", "影格分析失敗: ${t.message}")
            }
        })
    }

    /**
     * 🌟 連續 3 次診斷計數：更新 APP 文字，連擊滿 3 次觸發系統通知（1小時冷卻）
     */
    private fun handleDiagnosisResult(diseaseName: String) {
        mainHandler.post {
            val isHealthy = diseaseName.contains("健康") || diseaseName.lowercase().contains("healthy")

            // 1. 如果恢復健康：重置計數與通知冷卻時間
            if (isHealthy) {
                streakCount = 0
                lastDiseaseName = diseaseName
                lastAlertTime = 0L
                activity.updateDiagnosisUI(diseaseName, streakCount)
                return@post
            }

            // 2. 累積同種病害命中次數
            if (diseaseName == lastDiseaseName) {
                streakCount++
            } else {
                streakCount = 1
                lastDiseaseName = diseaseName
                lastAlertTime = 0L
            }

            // 3. 純粹更新 APP 畫面上的診斷與命中數字
            activity.updateDiagnosisUI(diseaseName, streakCount)

            // 4. 連續滿 3 次，且超過 1 小時冷卻期，觸發手機系統頂部下拉通知
            val currentTime = System.currentTimeMillis()
            if (streakCount >= 3 && (currentTime - lastAlertTime >= alertCooldownMillis)) {
                lastAlertTime = currentTime

                // 發送 Android 手機系統通知列訊息
                activity.sendAlertNotification(diseaseName)
            }
        }
    }
}