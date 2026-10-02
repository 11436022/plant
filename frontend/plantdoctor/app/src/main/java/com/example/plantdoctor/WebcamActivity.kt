package com.example.plantdoctor

import android.Manifest
import android.app.NotificationChannel
import android.app.NotificationManager
import android.content.Context
import android.content.pm.PackageManager
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.ImageFormat
import android.graphics.Rect
import android.graphics.RectF
import android.graphics.YuvImage
import android.os.Build
import android.os.Bundle
import android.os.Environment
import android.os.Handler
import android.os.Looper
import android.text.Editable
import android.text.TextWatcher
import android.util.Log
import android.view.LayoutInflater
import android.view.MotionEvent
import android.view.View
import android.view.ViewGroup
import android.view.WindowManager
import android.widget.*
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.camera.core.CameraSelector
import androidx.camera.core.ImageAnalysis
import androidx.camera.core.ImageProxy
import androidx.camera.core.Preview
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.camera.view.PreviewView
import androidx.constraintlayout.widget.ConstraintLayout
import androidx.core.app.NotificationCompat
import androidx.core.content.ContextCompat
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.google.gson.Gson
import com.google.gson.reflect.TypeToken
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.asRequestBody
import okhttp3.RequestBody.Companion.toRequestBody
import retrofit2.Call
import retrofit2.Callback
import retrofit2.Response
import java.io.ByteArrayOutputStream
import java.io.File
import java.io.FileOutputStream
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.IdentityHashMap
import java.util.UUID
import java.util.concurrent.Executors

class WebcamActivity : AppCompatActivity() {

    // UI 元件
    private lateinit var webcamRoot: ConstraintLayout
    private lateinit var previewView: PreviewView
    private lateinit var boxOverlay: InteractiveBoxView
    private lateinit var rgMode: RadioGroup
    private lateinit var rbSingleMode: RadioButton
    private lateinit var rbMultiMode: RadioButton
    private lateinit var btnAddRegion: Button
    private lateinit var btnPowerSave: ImageButton

    private lateinit var tvStatus: TextView
    private lateinit var tvDiagnosis: TextView
    private lateinit var tvStreak: TextView
    private lateinit var btnToggleMonitor: Button

    // 單植物控制元件
    private lateinit var layoutSingleControl: LinearLayout
    private lateinit var sbSingleInterval: SeekBar
    private lateinit var etSingleInterval: EditText

    // 多植物控制元件與列表
    private lateinit var layoutMultiControl: LinearLayout
    private lateinit var rvMultiRegions: RecyclerView
    private lateinit var multiRegionAdapter: MultiRegionAdapter

    // 省電覆蓋層
    private lateinit var layoutPowerSaveOverlay: FrameLayout

    // 策略與數據
    private lateinit var singleStrategy: SinglePlantMonitorStrategy
    private val cropZoneList = mutableListOf<CropZone>()
    private var monitoringSessionId: String? = null
    private val regionIds = IdentityHashMap<CropZone, String>()
    private val pendingUploads = mutableMapOf<String, Call<WebcamAnalyzeResponse>>()
    private val notifiedAlertIds = mutableSetOf<Int>()
    private var backendStatusText = ""

    // 狀態變數
    private var isMonitoring = false
    var sampleIntervalSeconds = 120L // 預設 2 分鐘 (120秒)
        private set

    // 音效與排程 Handler
    private val windHandler = Handler(Looper.getMainLooper())
    private val windRunnable = Runnable { SoundManager.startWind() }

    private val powerSaveHandler = Handler(Looper.getMainLooper())
    private val autoPowerSaveRunnable = Runnable { enterPowerSaveMode() }

    private val cameraExecutor = Executors.newSingleThreadExecutor()

    // 組別與 Coroutines 變數
    private lateinit var btnSelectSession: TextView
    private val sessionList = mutableListOf<PlantSession>()
    private var currentSession: PlantSession? = null
    private var monitorJob: Job? = null

    // 📸 紀錄本次開啟監測後的總拍照/分析次數
    private var totalCaptureCount = 0
    private lateinit var btnBackHome: ImageButton

    // 權限請求處理
    private val requestPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { isGranted ->
        if (isGranted) {
            startCamera()
        } else {
            Toast.makeText(this, "需要相機權限才能進行即時監控", Toast.LENGTH_SHORT).show()
            finish()
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        setContentView(R.layout.activity_webcam)

        bindViews()
        setupMultiRecyclerView()
        setupListeners()
        setupSingleIntervalControls()

        singleStrategy = SinglePlantMonitorStrategy(this)

        checkCameraPermission()
        resetAutoPowerSaveTimer()

        boxOverlay.visibility = View.VISIBLE
        singleStrategy.showCenterCropZone(boxOverlay)
        setupSessionControls()
    }

    private fun bindViews() {
        webcamRoot = findViewById(R.id.webcam_root_layout)
        previewView = findViewById(R.id.previewView)
        boxOverlay = findViewById(R.id.overlayCanvas)

        rgMode = findViewById(R.id.rgMode)
        rbSingleMode = findViewById(R.id.rbSingleMode)
        rbMultiMode = findViewById(R.id.rbMultiMode)
        btnAddRegion = findViewById(R.id.btnAddRegion)
        btnPowerSave = findViewById(R.id.btnPowerSave)

        tvStatus = findViewById(R.id.tvStatus)
        tvDiagnosis = findViewById(R.id.tvDiagnosis)
        tvStreak = findViewById(R.id.tvStreak)
        btnToggleMonitor = findViewById(R.id.btnToggleMonitor)

        layoutSingleControl = findViewById(R.id.layoutSingleControl)
        sbSingleInterval = findViewById(R.id.sbSingleInterval)
        etSingleInterval = findViewById(R.id.etSingleInterval)

        layoutMultiControl = findViewById(R.id.layoutMultiControl)
        rvMultiRegions = findViewById(R.id.rvMultiRegions)
        layoutPowerSaveOverlay = findViewById(R.id.layoutPowerSaveOverlay)

        // 在 bindViews() 裡面：
        btnBackHome = findViewById(R.id.btn_back_home)

        // 點擊事件：播放音效並結束當前頁面返回主頁
        btnBackHome.setOnClickListener {
            SoundManager.playBubblePop()
            finish()
        }
    }

    private fun setupMultiRecyclerView() {
        multiRegionAdapter = MultiRegionAdapter(
            cropZoneList,
            onItemClick = { zone -> showZoneOptionDialog(zone) }
        )
        rvMultiRegions.layoutManager = LinearLayoutManager(this)
        rvMultiRegions.adapter = multiRegionAdapter
    }

    private fun setupListeners() {
        btnToggleMonitor.setOnClickListener {
            SoundManager.playBubblePop()
            resetAutoPowerSaveTimer()
            isMonitoring = !isMonitoring

            // 🌟 只要切換開關，立刻將次數歸零
            totalCaptureCount = 0

            if (isMonitoring) {
                btnToggleMonitor.text = "停止即時監控"
                tvStatus.text = "狀態：監控中..."
                Log.d("WEBCAM_PROD", "🚀 [點擊按鈕] 開始即時監控！模式：${if (rgMode.checkedRadioButtonId == R.id.rbSingleMode) "單植物" else "多植物"}")

                // 🌟 1. 立刻更新 UI 畫面上的數字為 0 次
                updateDiagnosisUI("準備中...", totalCaptureCount)

                startMonitoringLoop()
            } else {
                btnToggleMonitor.text = "開始即時監控"
                tvStatus.text = "狀態：已暫停"
                Log.d("WEBCAM_PROD", "🛑 [點擊按鈕] 停止監控！")

                stopMonitoring()
            }
        }

        rgMode.setOnCheckedChangeListener { _, checkedId ->
            SoundManager.playBubblePop()
            resetAutoPowerSaveTimer()

            // 🌟 切換模式時也將次數歸零並更新 UI
            totalCaptureCount = 0
            updateDiagnosisUI("待命", totalCaptureCount)

            if (checkedId == R.id.rbSingleMode) {
                layoutSingleControl.visibility = View.VISIBLE
                layoutMultiControl.visibility = View.GONE
                btnAddRegion.visibility = View.GONE
                boxOverlay.visibility = View.VISIBLE
                singleStrategy.showCenterCropZone(boxOverlay)
            } else {
                layoutSingleControl.visibility = View.GONE
                layoutMultiControl.visibility = View.VISIBLE
                btnAddRegion.visibility = View.VISIBLE

                boxOverlay.visibility = View.VISIBLE
                boxOverlay.updateZones(cropZoneList, editable = true)

                if (cropZoneList.isEmpty()) {
                    addNewCropZone()
                }
            }
            if (isMonitoring) startMonitoringLoop()
        }

        btnPowerSave.setOnClickListener {
            SoundManager.playBubblePop()
            enterPowerSaveMode()
        }

        layoutPowerSaveOverlay.setOnClickListener {
            SoundManager.playBubblePop()
            exitPowerSaveMode()
        }

        btnAddRegion.setOnClickListener {
            SoundManager.playBubblePop()
            resetAutoPowerSaveTimer()
            addNewCropZone()
        }
    }

    /**
     * 🌟 監控主循環 (使用 Coroutine 輪詢)
     */
    private fun cancelMonitoringRequests() {
        monitorJob?.cancel()
        monitorJob = null
        monitoringSessionId = null
        val calls = pendingUploads.values.toList()
        pendingUploads.clear()
        calls.forEach { it.cancel() }
        regionIds.clear()
    }

    private fun stopMonitoring() {
        isMonitoring = false
        cancelMonitoringRequests()
        totalCaptureCount = 0
        backendStatusText = ""
        btnToggleMonitor.text = "開始即時監控"
        updateDiagnosisUI("已暫停", totalCaptureCount)
    }

    private fun startMonitoringLoop() {
        cancelMonitoringRequests()
        if (!isMonitoring) return
        monitoringSessionId = UUID.randomUUID().toString()
        totalCaptureCount = 0
        backendStatusText = ""
        notifiedAlertIds.clear()
        currentSession?.cropZones?.forEach { it.lastCapturedTime = 0L }
        updateDiagnosisUI("準備中...", totalCaptureCount)

        // Keep mutable zones, request bookkeeping and UI on the main thread.
        monitorJob = lifecycleScope.launch {
            while (isActive && isMonitoring) {
                if (rgMode.checkedRadioButtonId == R.id.rbSingleMode) {
                    val intervalSec = (etSingleInterval.text.toString().toIntOrNull() ?: 120)
                        .coerceIn(30, 600)
                    delay(intervalSec * 1000L)
                    captureSinglePlant()
                } else {
                    val currentTime = System.currentTimeMillis()
                    val zones = currentSession?.cropZones?.toList().orEmpty()
                    for (zone in zones) {
                        if (!zone.isEnabled) continue
                        val intervalMs = zone.intervalMinutes.coerceIn(30L, 600L) * 1000L
                        if (currentTime - zone.lastCapturedTime >= intervalMs) {
                            captureAndAnalyzeCropZone(zone)
                            zone.lastCapturedTime = currentTime
                        }
                    }
                    delay(1000L)
                }
            }
        }
    }

    private fun captureSinglePlant() {
        if (!isMonitoring || pendingUploads.containsKey("single")) return
        val bitmap = previewView.bitmap
        if (bitmap == null) {
            Log.e("WEBCAM_PROD", "❌ 單植物模式拍照失敗：PreviewView 為空")
            return
        }


        val username = getUserName()
        val sessionName = currentSession?.name ?: "組別一"
        val timeStamp = SimpleDateFormat("yyyyMMdd_HHmmss", Locale.getDefault()).format(Date())
        val fileName = "${username}_${sessionName}_${timeStamp}_single.jpg"

        val centerRect = RectF(0.2f, 0.2f, 0.8f, 0.8f)
        val croppedFile = cropBitmapToTempFile(bitmap, centerRect, 0)

        if (croppedFile != null && croppedFile.exists()) {
            uploadCropZoneImageToBackend(croppedFile, fileName, "single", "單植物")
        }
    }

    private fun addNewCropZone() {
        val session = currentSession ?: return
        val nextId = (cropZoneList.maxOfOrNull { it.id } ?: 0) + 1
        val offset = ((nextId - 1) % 3) * 0.12f
        val newZone = CropZone(
            id = nextId,
            name = "植物 %02d".format(nextId),
            rectNorm = RectF(0.15f + offset, 0.15f + offset, 0.45f + offset, 0.55f + offset),
            intervalMinutes = 120
        )
        cropZoneList.add(newZone)
        session.cropZones.add(newZone)
        saveSessionsToStorage()
        boxOverlay.updateZones(cropZoneList, editable = true)
        multiRegionAdapter.notifyDataSetChanged()
        Toast.makeText(this, "已建立【${newZone.name}】選取框", Toast.LENGTH_SHORT).show()
    }

    private fun showZoneOptionDialog(zone: CropZone) {
        val options = arrayOf("修改名稱與採樣時間", "刪除此區域")
        val mainColor = getThemeMainColor()

        val dialog = AlertDialog.Builder(this)
            .setTitle("管理區域：${zone.name}")
            .setItems(options) { _, which ->
                when (which) {
                    0 -> showEditZoneDialog(zone)
                    1 -> deleteCropZone(zone)
                }
            }
            .setNegativeButton("取消", null)
            .create()

        dialog.show()

        // 🌟 注入主題深色圓角背景
        applyDialogTheme(dialog)

        dialog.getButton(AlertDialog.BUTTON_NEGATIVE)?.setTextColor(mainColor)
    }

    private fun showEditZoneDialog(zone: CropZone) {
        val dialogView = LayoutInflater.from(this).inflate(R.layout.dialog_edit_zone, null, false)
        val etName = dialogView.findViewById<EditText>(R.id.etZoneName)
        val sbInterval = dialogView.findViewById<SeekBar>(R.id.sbDialogInterval)
        val etInterval = dialogView.findViewById<EditText>(R.id.etDialogInterval)

        // 🌟 確保輸入框文字在深色主題底色下清晰可見
        etName.setTextColor(android.graphics.Color.WHITE)
        etInterval.setTextColor(android.graphics.Color.WHITE)

        // 🌟 注入當前主題色至 Dialog 內的 SeekBar
        val mainColor = getThemeMainColor()
        val colorStateList = android.content.res.ColorStateList.valueOf(mainColor)
        sbInterval.thumbTintList = colorStateList
        sbInterval.progressTintList = colorStateList

        etName.setText(zone.name)
        val currentSec: Int = zone.intervalMinutes.toInt().coerceIn(30, 600)
        sbInterval.progress = currentSec
        etInterval.setText(currentSec.toString())

        sbInterval.setOnSeekBarChangeListener(object : SeekBar.OnSeekBarChangeListener {
            override fun onProgressChanged(seekBar: SeekBar?, progress: Int, fromUser: Boolean) {
                if (fromUser) {
                    etInterval.setText(progress.toString())
                }
            }
            override fun onStartTrackingTouch(seekBar: SeekBar?) {}
            override fun onStopTrackingTouch(seekBar: SeekBar?) {}
        })

        etInterval.addTextChangedListener(object : TextWatcher {
            override fun beforeTextChanged(s: CharSequence?, start: Int, count: Int, after: Int) {}
            override fun onTextChanged(s: CharSequence?, start: Int, before: Int, count: Int) {}
            override fun afterTextChanged(s: Editable?) {
                val sec = s.toString().toIntOrNull()
                if (sec != null && sec in 30..600) {
                    if (sbInterval.progress != sec) {
                        sbInterval.progress = sec
                    }
                }
            }
        })

        val dialog = AlertDialog.Builder(this)
            .setTitle("設定：${zone.name}")
            .setView(dialogView)
            .setPositiveButton("儲存") { _, _ ->
                val newName = etName.text.toString().trim()
                val newSec: Int = etInterval.text.toString().toIntOrNull() ?: currentSec

                if (newName.isNotEmpty()) zone.name = newName
                zone.intervalMinutes = newSec.toLong()

                boxOverlay.updateZones(cropZoneList, editable = true)
                multiRegionAdapter.notifyDataSetChanged()
                saveSessionsToStorage()
                Toast.makeText(this, "已更新設定！", Toast.LENGTH_SHORT).show()
            }
            .setNegativeButton("取消", null)
            .create()

        dialog.show()

        // 🌟 注入主題深色圓角背景
        applyDialogTheme(dialog)

        // 🌟 按鈕字體顏色強制跟隨主題色
        dialog.getButton(AlertDialog.BUTTON_POSITIVE)?.setTextColor(mainColor)
        dialog.getButton(AlertDialog.BUTTON_NEGATIVE)?.setTextColor(mainColor)
    }

    private fun deleteCropZone(zone: CropZone) {
        cropZoneList.remove(zone)
        currentSession?.cropZones?.remove(zone)
        boxOverlay.updateZones(cropZoneList, editable = true)
        multiRegionAdapter.notifyDataSetChanged()
        saveSessionsToStorage()
        if (isMonitoring) startMonitoringLoop()
        Toast.makeText(this, "已刪除區域", Toast.LENGTH_SHORT).show()
    }

    private fun captureAndAnalyzeCropZone(zone: CropZone) {
        if (!isMonitoring || !zone.isEnabled) return
        val regionId = regionIds.getOrPut(zone) { UUID.randomUUID().toString() }
        if (pendingUploads.containsKey(regionId)) return
        val currentBitmap = previewView.bitmap ?: return

        val sessionName = currentSession?.name ?: "組別一"
        val username = getUserName()

        val croppedFile = cropBitmapToTempFile(currentBitmap, zone.rectNorm, zone.id) ?: return

        val timeStamp = SimpleDateFormat("yyyyMMdd_HHmmss", Locale.getDefault()).format(Date())
        val plantStr = "plant%02d".format(zone.id)
        val customFileName = "${username}_${sessionName}_${timeStamp}_${plantStr}.jpg"

        uploadCropZoneImageToBackend(croppedFile, customFileName, regionId, zone.name)
    }

    /**
     * 🚀 正式上線：將照片發送給 PlantApiService analyzeWebcamFrame
     */
    private fun uploadCropZoneImageToBackend(
        file: File,
        customFileName: String,
        regionId: String,
        regionName: String
    ) {
        val requestSessionId = monitoringSessionId
        if (!isMonitoring || requestSessionId == null || pendingUploads.containsKey(regionId)) {
            file.delete()
            return
        }
        val token = getValidSavedToken()
        if (token.isNullOrEmpty()) {
            file.delete()
            stopMonitoring()
            Toast.makeText(this, "請先登入以使用即時監控", Toast.LENGTH_SHORT).show()
            return
        }

        val body = MultipartBody.Part.createFormData(
            "file", customFileName, file.asRequestBody("image/jpeg".toMediaTypeOrNull())
        )
        val textType = "text/plain".toMediaTypeOrNull()
        val request = PlantApiService.create(token).analyzeWebcamFrame(
            body,
            requestSessionId.toRequestBody(textType),
            regionId.toRequestBody(textType)
        )
        pendingUploads[regionId] = request
        totalCaptureCount++
        updateDiagnosisUI("$regionName：分析中...", totalCaptureCount)

        request.enqueue(object : Callback<WebcamAnalyzeResponse> {
            override fun onResponse(
                call: Call<WebcamAnalyzeResponse>,
                response: Response<WebcamAnalyzeResponse>
            ) {
                if (pendingUploads[regionId] === call) pendingUploads.remove(regionId)
                file.delete()
                if (!isMonitoring || monitoringSessionId != requestSessionId || isDestroyed) return
                val result = response.body()
                when {
                    response.isSuccessful && result != null && result.status == "success" ->
                        handleWebcamResult(result, requestSessionId, regionId, regionName)
                    response.code() == 401 -> {
                        stopMonitoring()
                        Toast.makeText(this@WebcamActivity, "登入已過期，請重新登入", Toast.LENGTH_SHORT).show()
                    }
                    else -> {
                        Log.w("WEBCAM_PROD", "Frame analysis failed: HTTP ${response.code()}")
                        updateDiagnosisUI("$regionName：分析失敗", totalCaptureCount)
                    }
                }
            }

            override fun onFailure(call: Call<WebcamAnalyzeResponse>, t: Throwable) {
                if (pendingUploads[regionId] === call) pendingUploads.remove(regionId)
                file.delete()
                if (call.isCanceled || !isMonitoring || monitoringSessionId != requestSessionId || isDestroyed) return
                Log.e("WEBCAM_PROD", "Frame analysis failed", t)
                updateDiagnosisUI("$regionName：連線失敗", totalCaptureCount)
            }
        })
    }

    private fun handleWebcamResult(
        result: WebcamAnalyzeResponse,
        sessionId: String,
        regionId: String,
        regionName: String
    ) {
        val alert = result.alert
        if (alert?.session_id != null && alert.session_id != sessionId) return
        if (alert?.region_id != null && alert.region_id != regionId) return
        val statusText = result.diagnosis.status_name?.takeIf { it.isNotBlank() } ?: "無法判定"
        val reviewText = when (result.diagnosis.requires_review) {
            true -> "（需要人工複核）"
            false -> ""
            null -> "（複核狀態未提供）"
        }
        backendStatusText = "$regionName：後端連續判定 ${result.monitoring.streak} 次（${result.monitoring.status}）"
        updateDiagnosisUI("$regionName：$statusText$reviewText", totalCaptureCount)

        // Only a newly created backend alert can produce a phone notification.
        if (result.monitoring.triggered && alert != null && notifiedAlertIds.add(alert.id)) {
            sendAlertNotification("$regionName：$statusText", alert.id)
            Toast.makeText(this, "後端已建立監控警報", Toast.LENGTH_LONG).show()
        }
    }

    fun uploadSinglePlantFrame(jpegBytes: ByteArray) {
        runOnUiThread {
            if (!isMonitoring || rgMode.checkedRadioButtonId != R.id.rbSingleMode ||
                pendingUploads.containsKey("single")) return@runOnUiThread
            var file: File? = null
            try {
                val frameFile = File.createTempFile("webcam_single_", ".jpg", cacheDir)
                file = frameFile
                frameFile.outputStream().use { it.write(jpegBytes) }
                uploadCropZoneImageToBackend(frameFile, "webcam_single.jpg", "single", "單植物")
            } catch (e: Exception) {
                file?.delete()
                Log.e("WEBCAM_PROD", "Could not prepare single-plant frame", e)
            }
        }
    }

    private fun getUserSavedToken(): String? {
        val sharedPref = getSharedPreferences("PlantDoctorPrefs", MODE_PRIVATE)
        return sharedPref.getString("access_token", null)
    }

    private fun getUserName(): String {
        // 檔名修正為與 LoginActivity 一致的 "PlantDoctor"
        val sharedPref = getSharedPreferences("PlantDoctor", MODE_PRIVATE)
        return sharedPref.getString("username", "使用者") ?: "使用者"
    }

    private fun cropBitmapToTempFile(fullBitmap: Bitmap, boxNorm: RectF, plantIndex: Int): File? {
        return try {
            val w = fullBitmap.width
            val h = fullBitmap.height

            val left = (boxNorm.left * w).toInt().coerceIn(0, w - 1)
            val top = (boxNorm.top * h).toInt().coerceIn(0, h - 1)
            val right = (boxNorm.right * w).toInt().coerceIn(left + 1, w)
            val bottom = (boxNorm.bottom * h).toInt().coerceIn(top + 1, h)

            var croppedBitmap = Bitmap.createBitmap(fullBitmap, left, top, right - left, bottom - top)

            // 🌟 防禦機制：檢查是否小於後端要求的 320x240，太小就自動放大
            val minWidth = 320
            val minHeight = 240

            if (croppedBitmap.width < minWidth || croppedBitmap.height < minHeight) {
                val widthRatio = minWidth.toFloat() / croppedBitmap.width
                val heightRatio = minHeight.toFloat() / croppedBitmap.height
                // 取較大倍率，確保寬與高都至少達到 320x240
                val scaleFactor = Math.max(widthRatio, heightRatio)

                val targetWidth = (croppedBitmap.width * scaleFactor).toInt()
                val targetHeight = (croppedBitmap.height * scaleFactor).toInt()

                Log.d("WEBCAM_PROD", "📐 圖片過小 (${croppedBitmap.width}x${croppedBitmap.height})，強制放大至 ${targetWidth}x${targetHeight}")

                croppedBitmap = Bitmap.createScaledBitmap(croppedBitmap, targetWidth, targetHeight, true)
            }

            val outputFile = File.createTempFile("webcam_crop_${plantIndex}_", ".jpg", cacheDir)
            FileOutputStream(outputFile).use { out ->
                croppedBitmap.compress(Bitmap.CompressFormat.JPEG, 92, out)
            }
            outputFile
        } catch (e: Exception) {
            e.printStackTrace()
            null
        }
    }

    private fun setupSingleIntervalControls() {
        sbSingleInterval.setOnSeekBarChangeListener(object : SeekBar.OnSeekBarChangeListener {
            override fun onProgressChanged(seekBar: SeekBar?, progress: Int, fromUser: Boolean) {
                if (fromUser) {
                    sampleIntervalSeconds = progress.toLong()
                    etSingleInterval.setText(progress.toString())
                    resetAutoPowerSaveTimer()
                }
            }
            override fun onStartTrackingTouch(seekBar: SeekBar?) {}
            override fun onStopTrackingTouch(seekBar: SeekBar?) {}
        })

        etSingleInterval.addTextChangedListener(object : TextWatcher {
            override fun beforeTextChanged(s: CharSequence?, start: Int, count: Int, after: Int) {}
            override fun onTextChanged(s: CharSequence?, start: Int, before: Int, count: Int) {}
            override fun afterTextChanged(s: Editable?) {
                val inputSec: Long? = s.toString().toLongOrNull()
                if (inputSec != null && inputSec in 30..600) {
                    sampleIntervalSeconds = inputSec
                    val progressValue: Int = inputSec.toInt()
                    if (sbSingleInterval.progress != progressValue) {
                        sbSingleInterval.progress = progressValue
                    }
                    resetAutoPowerSaveTimer()
                }
            }
        })
    }

    private fun enterPowerSaveMode() {
        layoutPowerSaveOverlay.visibility = View.VISIBLE
        val layoutParams = window.attributes
        layoutParams.screenBrightness = 0.01f
        window.attributes = layoutParams

        SoundManager.stopBGM()
        SoundManager.stopWind()
        windHandler.removeCallbacks(windRunnable)
    }

    private fun exitPowerSaveMode() {
        layoutPowerSaveOverlay.visibility = View.GONE
        val layoutParams = window.attributes
        layoutParams.screenBrightness = WindowManager.LayoutParams.BRIGHTNESS_OVERRIDE_NONE
        window.attributes = layoutParams

        SoundManager.startBGM()
        resetAutoPowerSaveTimer()
    }

    private fun resetAutoPowerSaveTimer() {
        powerSaveHandler.removeCallbacks(autoPowerSaveRunnable)
        powerSaveHandler.postDelayed(autoPowerSaveRunnable, 30_000)
    }

    private fun checkCameraPermission() {
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.CAMERA)
            == PackageManager.PERMISSION_GRANTED
        ) {
            startCamera()
        } else {
            requestPermissionLauncher.launch(Manifest.permission.CAMERA)
        }
    }

    private fun startCamera() {
        val cameraProviderFuture = ProcessCameraProvider.getInstance(this)
        cameraProviderFuture.addListener({
            val cameraProvider = cameraProviderFuture.get()

            val preview = Preview.Builder().build().also {
                it.setSurfaceProvider(previewView.surfaceProvider)
            }

            val imageAnalyzer = ImageAnalysis.Builder()
                .setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST)
                .build()
                .also {
                    it.setAnalyzer(cameraExecutor) { imageProxy ->
                        processFrame(imageProxy)
                    }
                }

            val cameraSelector = CameraSelector.DEFAULT_BACK_CAMERA

            try {
                cameraProvider.unbindAll()
                cameraProvider.bindToLifecycle(
                    this, cameraSelector, preview, imageAnalyzer
                )
            } catch (e: Exception) {
                Log.e("WEBCAM", "相機啟動失敗: ${e.message}")
            }
        }, ContextCompat.getMainExecutor(this))
    }

    private fun processFrame(image: ImageProxy) {
        // startMonitoringLoop owns capture scheduling in both modes.
        image.close()
    }

    fun sendAlertNotification(diagnosisName: String, notificationId: Int = 1001) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            if (ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS)
                != PackageManager.PERMISSION_GRANTED
            ) {
                requestPermissions(arrayOf(Manifest.permission.POST_NOTIFICATIONS), 101)
                return
            }
        }

        val notificationManager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        val channelId = "webcam_alert_channel"

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                channelId,
                "植物監控警報",
                NotificationManager.IMPORTANCE_HIGH
            )
            notificationManager.createNotificationChannel(channel)
        }

        val notification = NotificationCompat.Builder(this, channelId)
            .setSmallIcon(R.drawable.ic_camera)
            .setContentTitle("🚨 植物健康警告！")
            .setContentText("即時監控診斷異常：$diagnosisName")
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .setAutoCancel(true)
            .build()

        notificationManager.notify(notificationId, notification)
    }

    /**
     * 🌟 當 InupdateteractiveBoxView 手動拖移或縮放方框結束時由 View 觸發
     */
    fun onCropZonesChanged() {
        saveSessionsToStorage()
        if (isMonitoring) startMonitoringLoop()
    }

    override fun onResume() {
        super.onResume()
        resetAutoPowerSaveTimer()

        // 🌟 1. 基礎主題套用 (按鈕與基本元素)
        ThemeManager.applyTheme(
            context = this,
            rootLayout = webcamRoot,
            mainButtons = listOf(btnToggleMonitor, btnAddRegion),
            imageButtons = listOf(btnPowerSave,btnBackHome)

        )

        // 🌟 2. Webcam 專屬主題套用 (控制面板、組別選取按鈕、SeekBar、RadioGroup)
        val bottomPanel = findViewById<LinearLayout>(R.id.bottomPanel)
        val sbSingleInterval = findViewById<SeekBar>(R.id.sbSingleInterval)
        val etSingleInterval = findViewById<EditText>(R.id.etSingleInterval)

        ThemeManager.applyThemeToWebcam(
            context = this,
            btnSelectSession = btnSelectSession,
            rbSingleMode = rbSingleMode,
            rbMultiMode = rbMultiMode,
            seekBar = sbSingleInterval,
            etInterval = etSingleInterval,
            panelBackground = bottomPanel
        )

        if (layoutPowerSaveOverlay.visibility != View.VISIBLE) {
            SoundManager.startBGM()
        }
    }

    override fun onTouchEvent(event: MotionEvent?): Boolean {
        resetAutoPowerSaveTimer()
        if (event != null) {
            when (event.action) {
                MotionEvent.ACTION_DOWN -> windHandler.postDelayed(windRunnable, 500)
                MotionEvent.ACTION_UP, MotionEvent.ACTION_CANCEL -> {
                    windHandler.removeCallbacks(windRunnable)
                    SoundManager.stopWind()
                }
            }
        }
        return super.onTouchEvent(event)
    }

    override fun onPause() {
        super.onPause()
        saveSessionsToStorage()
        powerSaveHandler.removeCallbacks(autoPowerSaveRunnable)
    }

    override fun onStop() {
        super.onStop()
        stopMonitoring()
        SoundManager.stopWind()
        windHandler.removeCallbacks(windRunnable)
    }

    override fun onDestroy() {
        cancelMonitoringRequests()
        super.onDestroy()
        powerSaveHandler.removeCallbacksAndMessages(null)
        windHandler.removeCallbacksAndMessages(null)
        cameraExecutor.shutdown()
        // 啟動監測或關閉監測時歸零
        totalCaptureCount = 0
    }

    inner class MultiRegionAdapter(
        private val list: List<CropZone>,
        private val onItemClick: (CropZone) -> Unit
    ) : RecyclerView.Adapter<MultiRegionAdapter.ViewHolder>() {

        inner class ViewHolder(v: View) : RecyclerView.ViewHolder(v) {
            val tvName: TextView = v.findViewById(android.R.id.text1)
            val tvSub: TextView = v.findViewById(android.R.id.text2)
        }

        override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ViewHolder {
            val view = LayoutInflater.from(parent.context)
                .inflate(android.R.layout.simple_list_item_2, parent, false)
            return ViewHolder(view)
        }

        override fun onBindViewHolder(holder: ViewHolder, position: Int) {
            val zone = list[position]
            holder.tvName.text = zone.name
            holder.tvSub.text = "採樣間隔：${zone.intervalMinutes} 秒"
            holder.itemView.setOnClickListener { onItemClick(zone) }
        }

        override fun getItemCount(): Int = list.size
    }

    // -------------------------------------------------------------
    // 組別 (Session) 管理與本地 SharedPreferences 讀存邏輯
    // -------------------------------------------------------------

    private fun setupSessionControls() {
        btnSelectSession = findViewById(R.id.btnSelectSession)

        loadSessionsFromStorage()
        updateSessionButtonText()
        loadCurrentSessionZones()

        btnSelectSession.setOnClickListener {
            showSessionSelectionDialog()
        }
    }

    private fun loadCurrentSessionZones() {
        val session = currentSession ?: return

        cropZoneList.clear()
        cropZoneList.addAll(session.cropZones)

        if (rgMode.checkedRadioButtonId == R.id.rbMultiMode) {
            boxOverlay.updateZones(cropZoneList, editable = true)
            multiRegionAdapter.notifyDataSetChanged()
        }
        if (isMonitoring) startMonitoringLoop()
    }

    private fun updateSessionButtonText() {
        val name = currentSession?.name ?: "未選擇組別"
        btnSelectSession.text = "$name ▼"
    }

    /**
     * 🌟 取得主題對應的主色調
     */
    private fun getThemeMainColor(): Int {
        val sharedPref = getSharedPreferences("PlantDoctor", MODE_PRIVATE)
        val themeId = sharedPref.getInt("THEME_COLOR_ID", 0)
        val colorStr = when (themeId) {
            1 -> "#64B5F6" // 藍
            2 -> "#FFCC80" // 棕
            3 -> "#F48FB1" // 粉
            else -> "#2E7D32" // 綠
        }
        return android.graphics.Color.parseColor(colorStr)
    }

    /**
     * 🌟 動態套用深色圓角背景與文字主題 (零改動原架構魔法)
     */
    private fun applyDialogTheme(dialog: AlertDialog) {
        val sharedPref = getSharedPreferences("PlantDoctor", MODE_PRIVATE)
        val themeId = sharedPref.getInt("THEME_COLOR_ID", 0)

        val bgColorStr = when (themeId) {
            1 -> "#1A237E" // 深藍底
            2 -> "#3E2723" // 深可可底
            3 -> "#4A0033" // 深莓紅底
            else -> "#FFFFFF" // 白底
        }

        dialog.window?.let { window ->
            val background = android.graphics.drawable.GradientDrawable().apply {
                setColor(android.graphics.Color.parseColor(bgColorStr))
                cornerRadius = 32f
            }
            window.setBackgroundDrawable(background)
        }
    }

    private fun showSessionSelectionDialog() {
        val options = mutableListOf<String>()

        sessionList.forEach { session ->
            val prefix = if (session == currentSession) "✓ " else "   "
            options.add("$prefix${session.name}")
        }

        options.add("➕ 管理/增刪改組別")

        val builder = AlertDialog.Builder(this)
            .setTitle("選擇植物組別")
            .setItems(options.toTypedArray()) { _, which ->
                if (which == options.size - 1) {
                    showManageSessionDialog()
                } else {
                    currentSession = sessionList[which]
                    updateSessionButtonText()
                    loadCurrentSessionZones()
                    Toast.makeText(this, "已切換至：${currentSession?.name}", Toast.LENGTH_SHORT).show()
                }
            }
            .setNegativeButton("取消", null)

        val dialog = builder.create()
        dialog.show()
        applyDialogTheme(dialog)
        dialog.getButton(AlertDialog.BUTTON_NEGATIVE)?.setTextColor(getThemeMainColor())
    }

    private fun showManageSessionDialog() {
        val manageOptions = arrayOf("新增新組別", "修改當前組別名稱", "刪除當前組別")
        val builder = AlertDialog.Builder(this)
            .setTitle("管理組別：${currentSession?.name}")
            .setItems(manageOptions) { _, which ->
                when (which) {
                    0 -> showAddSessionDialog()
                    1 -> showRenameSessionDialog()
                    2 -> deleteCurrentSession()
                }
            }
            .setNegativeButton("返回", null)

        val dialog = builder.create()
        dialog.show()
        applyDialogTheme(dialog)
        dialog.getButton(AlertDialog.BUTTON_NEGATIVE)?.setTextColor(getThemeMainColor())
    }

    private fun showAddSessionDialog() {
        val container = FrameLayout(this).apply {
            setPadding(50, 30, 50, 10)
        }
        val etInput = EditText(this).apply {
            hint = "例如：陽台花草組"
            setTextColor(android.graphics.Color.WHITE)
            setHintTextColor(android.graphics.Color.GRAY)
        }
        container.addView(etInput)

        val builder = AlertDialog.Builder(this)
            .setTitle("新增植物組別")
            .setView(container)
            .setPositiveButton("建立") { _, _ ->
                val name = etInput.text.toString().trim()
                if (name.isNotEmpty()) {
                    val newSession = PlantSession(name = name)
                    sessionList.add(newSession)
                    currentSession = newSession
                    updateSessionButtonText()
                    loadCurrentSessionZones()
                    saveSessionsToStorage()
                    Toast.makeText(this, "已建立並切換至：$name", Toast.LENGTH_SHORT).show()
                }
            }
            .setNegativeButton("取消", null)

        val dialog = builder.create()
        dialog.show()
        applyDialogTheme(dialog)

        val mainColor = getThemeMainColor()
        dialog.getButton(AlertDialog.BUTTON_POSITIVE)?.setTextColor(mainColor)
        dialog.getButton(AlertDialog.BUTTON_NEGATIVE)?.setTextColor(mainColor)
    }

    private fun showRenameSessionDialog() {
        val session = currentSession ?: return
        val container = FrameLayout(this).apply {
            setPadding(50, 30, 50, 10)
        }
        val etInput = EditText(this).apply {
            setText(session.name)
            setTextColor(android.graphics.Color.WHITE)
        }
        container.addView(etInput)

        val builder = AlertDialog.Builder(this)
            .setTitle("修改組別名稱")
            .setView(container)
            .setPositiveButton("確定") { _, _ ->
                val name = etInput.text.toString().trim()
                if (name.isNotEmpty()) {
                    session.name = name
                    updateSessionButtonText()
                    saveSessionsToStorage()
                    Toast.makeText(this, "已修改名稱為：$name", Toast.LENGTH_SHORT).show()
                }
            }
            .setNegativeButton("取消", null)

        val dialog = builder.create()
        dialog.show()
        applyDialogTheme(dialog)

        val mainColor = getThemeMainColor()
        dialog.getButton(AlertDialog.BUTTON_POSITIVE)?.setTextColor(mainColor)
        dialog.getButton(AlertDialog.BUTTON_NEGATIVE)?.setTextColor(mainColor)
    }

    private fun deleteCurrentSession() {
        val session = currentSession ?: return

        if (sessionList.size <= 1) {
            Toast.makeText(this, "至少需保留一個組別！", Toast.LENGTH_SHORT).show()
            return
        }

        val builder = AlertDialog.Builder(this)
            .setTitle("刪除組別")
            .setMessage("確定要刪除【${session.name}】及其內部所有區域設定嗎？")
            .setPositiveButton("刪除") { _, _ ->
                sessionList.remove(session)
                currentSession = sessionList[0]
                updateSessionButtonText()
                loadCurrentSessionZones()
                saveSessionsToStorage()
                Toast.makeText(this, "已刪除該組別", Toast.LENGTH_SHORT).show()
            }
            .setNegativeButton("取消", null)

        val dialog = builder.create()
        dialog.show()
        applyDialogTheme(dialog)

        val mainColor = getThemeMainColor()
        dialog.getButton(AlertDialog.BUTTON_POSITIVE)?.setTextColor(android.graphics.Color.RED)
        dialog.getButton(AlertDialog.BUTTON_NEGATIVE)?.setTextColor(mainColor)
    }

    /**
     * 💾 將所有的 Session 資料永久儲存到手機本地 (SharedPreferences)
     */
    private fun saveSessionsToStorage() {
        val sharedPref = getSharedPreferences("PlantDoctorSessions", MODE_PRIVATE)
        val gson = Gson()
        val jsonString = gson.toJson(sessionList)
        sharedPref.edit().putString("saved_sessions", jsonString).apply()
    }

    /**
     * 📂 從手機本地讀取先前儲存的 Session 資料
     */
    private fun loadSessionsFromStorage() {
        val sharedPref = getSharedPreferences("PlantDoctorSessions", MODE_PRIVATE)
        val jsonString = sharedPref.getString("saved_sessions", null)

        sessionList.clear()

        if (!jsonString.isNullOrEmpty()) {
            try {
                val gson = Gson()
                val type = object : TypeToken<MutableList<PlantSession>>() {}.type
                val savedList: MutableList<PlantSession> = gson.fromJson(jsonString, type)
                sessionList.addAll(savedList)
            } catch (e: Exception) {
                e.printStackTrace()
            }
        }

        // 如果沒有任何歷史紀錄，則建立一個預設的組別
        if (sessionList.isEmpty()) {
            val defaultSession = PlantSession(name = "組別一")
            sessionList.add(defaultSession)
            saveSessionsToStorage()
        }

        currentSession = sessionList[0]
    }

    /**
     * 🔒 即時從 SharedPreferences 讀取使用者 Token
     */
    private fun getValidSavedToken(): String? {
        // 🌟 核心修正：名稱改成與 LoginActivity 完全一致的 "PlantDoctor"
        val sharedPref = getSharedPreferences("PlantDoctor", MODE_PRIVATE)

        // 🌟 key 名稱對齊 LoginActivity 的 "token"
        val token = sharedPref.getString("token", null)

        if (token.isNullOrEmpty()) {
            Log.e("WEBCAM_PROD", "❌ 無法從 SharedPreferences 找到 token！")
        } else {
            Log.d("WEBCAM_PROD", "🔑 成功讀取 Token！前 10 碼: ${token.take(10)}...")
        }

        return token
    }

    /**
     * 🌟 診斷結果與偵測次數 UI 更新函式
     */
    fun updateDiagnosisUI(statusText: String, captureCount: Int) {
        runOnUiThread {
            tvStatus.text = if (isMonitoring) "狀態：監控中..." else "狀態：已暫停"
            tvDiagnosis.text = "最新診斷：$statusText"
            tvStreak.text = "本次偵測次數：$captureCount 次" +
                if (backendStatusText.isNotEmpty()) "\n$backendStatusText" else ""
        }
    }

}

