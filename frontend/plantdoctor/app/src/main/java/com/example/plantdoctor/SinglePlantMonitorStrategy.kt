package com.example.plantdoctor

import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.ImageFormat
import android.graphics.Rect
import android.graphics.RectF
import android.graphics.YuvImage
import android.util.Log
import androidx.camera.core.ImageProxy
import java.io.ByteArrayOutputStream
import kotlin.math.min

class SinglePlantMonitorStrategy(private val activity: WebcamActivity) {

    private var lastSampleTime = 0L
    /**
     * 🌟 顯示單植物「正中心 1:1 方框」於畫面上
     * 歸一化座標：left=0.2, top=0.2, right=0.8, bottom=0.8 (大致為正中心區域)
     */
    fun showCenterCropZone(boxOverlay: InteractiveBoxView) {
        val centerZone = CropZone(
            id = 999,
            name = "單植物目標區 (正中心)",
            rectNorm = RectF(0.2f, 0.2f, 0.8f, 0.8f),
            intervalMinutes = 0
        )
        boxOverlay.updateZones(listOf(centerZone), editable = false)
    }

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

            // 🌟 核心：確定裁切正中心 1:1 正方形區域
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
        // Share session IDs, request lifecycle and backend-only alert handling.
        activity.uploadSinglePlantFrame(jpegBytes)
    }
}
