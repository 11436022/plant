package com.example.plantdoctor

import android.graphics.Bitmap
import android.graphics.RectF
import android.os.Bundle
import android.widget.Button
import android.widget.EditText
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.example.plantdoctor.PlantUploadHelper
import retrofit2.Call
import retrofit2.Callback
import retrofit2.Response
import java.io.File
import java.io.FileOutputStream
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import android.graphics.Color


class MultiPlantActivity : AppCompatActivity() {

    private lateinit var etSessionName: EditText
    private lateinit var btnAddPlant: Button
    private lateinit var recyclerViewPlants: RecyclerView
    private lateinit var boxOverlay: InteractiveBoxView

    private val plantList = mutableListOf<PlantCardItem>()
    private val zoneList = mutableListOf<CropZone>() // 儲存所有的 CropZone
    private lateinit var adapter: PlantAdapter
    private var currentUsername: String = "陳小華"

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_multi_plant)

        initViews()
        setupRecyclerView()

        // 預設建立第一個植物與對應的 CropZone
        addNewPlantWithCropZone()
    }

    private fun initViews() {
        etSessionName = findViewById(R.id.etSessionName)
        btnAddPlant = findViewById(R.id.btnAddPlant)
        recyclerViewPlants = findViewById(R.id.recyclerViewPlants)
        boxOverlay = findViewById(R.id.boxOverlay)

        btnAddPlant.setOnClickListener {
            addNewPlantWithCropZone()
        }
    }

    private fun setupRecyclerView() {
        adapter = PlantAdapter(plantList) { plantItem, position ->
            // 觸發該植物獨立的裁切與上傳檢測
            startCaptureAndAnalyze(plantItem, position)
        }
        recyclerViewPlants.layoutManager = LinearLayoutManager(this)
        recyclerViewPlants.adapter = adapter
    }

    /**
     * 新增一株植物卡片，並同步建立專屬的 CropZone 選取框
     */
    private fun addNewPlantWithCropZone() {
        val nextIndex = plantList.size + 1
        val plantName = "植物 %02d".format(nextIndex)

        // 1. 產生交錯位置的預設選取框 (CropZone)
        val offset = ((nextIndex - 1) % 3) * 0.15f
        val defaultRect = RectF(0.1f + offset, 0.1f + offset, 0.4f + offset, 0.5f + offset)

        val newZone = CropZone(
            id = nextIndex,
            name = plantName,
            rectNorm = defaultRect,
            intervalMinutes = 30 // 預設 30 分鐘定時拍攝
        )
        zoneList.add(newZone)

        // 2. 建立對應的 PlantCardItem 卡片
        val newPlant = PlantCardItem(
            plantIndex = nextIndex,
            name = plantName
        )
        plantList.add(newPlant)

        // 3. 同步刷新選取框 View 與卡片列表
        boxOverlay.updateZones(zoneList)
        adapter.notifyItemInserted(plantList.size - 1)
    }

    /**
     * 觸發檢測：拿全景照片 ➔ 依該植物的 CropZone 座標進行裁切 ➔ 打包上傳 API
     */
    private fun startCaptureAndAnalyze(plantItem: PlantCardItem, position: Int) {
        val sessionName = etSessionName.text.toString().trim().ifEmpty { "DefaultGroup" }
        val targetZone = zoneList.getOrNull(position)

        if (targetZone == null) {
            Toast.makeText(this, "找不到對應的選取框資料", Toast.LENGTH_SHORT).show()
            return
        }

        plantItem.isAnalyzing = true
        adapter.updateItem(position)

        // 1. 取得全景照片 Bitmap (對接 CameraX 實體視角截圖)
        val fullCameraBitmap = getFullCameraFrameBitmap()

        if (fullCameraBitmap == null) {
            Toast.makeText(this, "無法取得相機畫面", Toast.LENGTH_SHORT).show()
            plantItem.isAnalyzing = false
            adapter.updateItem(position)
            return
        }

        // 2. ✂️ 使用對應 CropZone 的 rectNorm 進行無損裁切
        val croppedImageFile = cropBitmapToTempFile(fullCameraBitmap, targetZone.rectNorm, plantItem.plantIndex)

        // 3. 使用 PlantUploadHelper 打包檔名 (例如: 陳小華_陽台花草組_20260725_154400_plant01.jpg)
        val imagePart = PlantUploadHelper.createPlantImagePart(
            username = currentUsername,
            sessionName = sessionName,
            plantIndex = plantItem.plantIndex,
            imageFile = croppedImageFile
        )

        // 4. 發送 API 診斷
        PlantApiService.create().analyzeWebcamFrame(imagePart).enqueue(object : Callback<WebcamAnalyzeResponse> {
            override fun onResponse(
                call: Call<WebcamAnalyzeResponse>,
                response: Response<WebcamAnalyzeResponse>
            ) {
                plantItem.isAnalyzing = false

                if (response.isSuccessful && response.body() != null) {
                    val body = response.body()!!
                    val crop = body.diagnosis.crop_name ?: "未知植物"
                    val status = body.diagnosis.status_name ?: "健康"

                    val timeFormatter = SimpleDateFormat("yyyy/MM/dd HH:mm:ss", Locale.getDefault())
                    val currentTimeStr = timeFormatter.format(Date())

                    // 5. 精準更新該植物卡片與 CropZone 拍攝紀錄
                    plantItem.lastDiagnosis = "$crop - $status"
                    plantItem.lastConfidence = body.diagnosis.confidence
                    plantItem.lastCapturedTime = currentTimeStr

                    targetZone.lastShotTimestamp = System.currentTimeMillis()

                    Toast.makeText(this@MultiPlantActivity, "${plantItem.name} 裁切上傳成功！", Toast.LENGTH_SHORT).show()
                } else {
                    Toast.makeText(this@MultiPlantActivity, "分析失敗 (${response.code()})", Toast.LENGTH_SHORT).show()
                }
                adapter.updateItem(position)
            }

            override fun onFailure(call: Call<WebcamAnalyzeResponse>, t: Throwable) {
                plantItem.isAnalyzing = false
                adapter.updateItem(position)
                Toast.makeText(this@MultiPlantActivity, "連線失敗: ${t.message}", Toast.LENGTH_SHORT).show()
            }
        })
    }

    /**
     * ✂️ 根據 CropZone 歸一化座標，將 Bitmap 裁切並儲存為檔案
     */
    private fun cropBitmapToTempFile(fullBitmap: Bitmap, boxNorm: RectF, plantIndex: Int): File {
        val w = fullBitmap.width
        val h = fullBitmap.height

        val left = (boxNorm.left * w).toInt().coerceIn(0, w - 1)
        val top = (boxNorm.top * h).toInt().coerceIn(0, h - 1)
        val right = (boxNorm.right * w).toInt().coerceIn(left + 1, w)
        val bottom = (boxNorm.bottom * h).toInt().coerceIn(top + 1, h)

        val croppedBitmap = Bitmap.createBitmap(fullBitmap, left, top, right - left, bottom - top)

        val outputFile = File(cacheDir, "crop_plant_$plantIndex.jpg")
        FileOutputStream(outputFile).use { out ->
            croppedBitmap.compress(Bitmap.CompressFormat.JPEG, 92, out)
        }
        return outputFile
    }

    // 模擬相機 full-frame Bitmap (未來對接 CameraX 實體 Preview 畫面)
    private fun getFullCameraFrameBitmap(): Bitmap? {
        val b = Bitmap.createBitmap(1080, 1920, Bitmap.Config.ARGB_8888)
        b.eraseColor(Color.DKGRAY)
        return b
    }
}