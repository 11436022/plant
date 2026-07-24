package com.example.plantdoctor

import android.Manifest
import android.app.NotificationChannel
import android.app.NotificationManager
import android.content.Context
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.text.Editable
import android.text.TextWatcher
import android.util.Log
import android.view.MotionEvent
import android.view.View
import android.view.WindowManager
import android.widget.*
import androidx.activity.result.contract.ActivityResultContracts
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
import java.util.concurrent.Executors

class WebcamActivity : AppCompatActivity() {

    // UI 元件
    private lateinit var webcamRoot: ConstraintLayout
    private lateinit var previewView: PreviewView
    private lateinit var overlayCanvas: View
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

    // 多植物控制元件
    private lateinit var layoutMultiControl: LinearLayout

    // 省電覆蓋層
    private lateinit var layoutPowerSaveOverlay: FrameLayout

    // 策略模組
    private lateinit var singleStrategy: SinglePlantMonitorStrategy

    // 狀態變數
    private var isMonitoring = false
    var sampleIntervalSeconds = 120L // 預設 2 分鐘 (120秒)
        private set

    // 音效與風聲 Handler
    private val windHandler = Handler(Looper.getMainLooper())
    private val windRunnable = Runnable { SoundManager.startWind() }

    // 30秒自動進入省電 Handler
    private val powerSaveHandler = Handler(Looper.getMainLooper())
    private val autoPowerSaveRunnable = Runnable { enterPowerSaveMode() }

    private val cameraExecutor = Executors.newSingleThreadExecutor()

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
        // 保持螢幕常亮（適合掛機）
        window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        setContentView(R.layout.activity_webcam)

        bindViews()
        setupListeners()
        setupSingleIntervalControls()

        // 初始化單植物策略模組
        singleStrategy = SinglePlantMonitorStrategy(this)

        checkCameraPermission()
        resetAutoPowerSaveTimer()
    }

    private fun bindViews() {
        webcamRoot = findViewById(R.id.webcam_root_layout)
        previewView = findViewById(R.id.previewView)
        overlayCanvas = findViewById(R.id.overlayCanvas)
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
        layoutPowerSaveOverlay = findViewById(R.id.layoutPowerSaveOverlay)
    }

    private fun setupListeners() {
        // 開始/暫停監控按鈕
        btnToggleMonitor.setOnClickListener {
            SoundManager.playBubblePop()
            resetAutoPowerSaveTimer()
            isMonitoring = !isMonitoring
            if (isMonitoring) {
                btnToggleMonitor.text = "停止即時監控"
                tvStatus.text = "狀態：監控中..."
            } else {
                btnToggleMonitor.text = "開始即時監控"
                tvStatus.text = "狀態：已暫停"
            }
        }

        // 模式切換 RadioGroup
        rgMode.setOnCheckedChangeListener { _, checkedId ->
            SoundManager.playBubblePop()
            resetAutoPowerSaveTimer()
            if (checkedId == R.id.rbSingleMode) {
                layoutSingleControl.visibility = View.VISIBLE
                layoutMultiControl.visibility = View.GONE
                btnAddRegion.visibility = View.GONE
            } else {
                layoutSingleControl.visibility = View.GONE
                layoutMultiControl.visibility = View.VISIBLE
                btnAddRegion.visibility = View.VISIBLE
            }
        }

        // 手動進入省電按鈕
        btnPowerSave.setOnClickListener {
            SoundManager.playBubblePop()
            enterPowerSaveMode()
        }

        // 點擊省電遮罩喚醒畫面
        layoutPowerSaveOverlay.setOnClickListener {
            SoundManager.playBubblePop()
            exitPowerSaveMode()
        }

        // 新增區域按鈕 (預留給多植物模式)
        btnAddRegion.setOnClickListener {
            SoundManager.playBubblePop()
            resetAutoPowerSaveTimer()
            Toast.makeText(this, "新增區域功能將於多植物模式啟用", Toast.LENGTH_SHORT).show()
        }
    }

    /**
     * 🌟 單植物模式：SeekBar 與 EditText 雙向同步連動 (範圍 30秒 ~ 600秒)
     */
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
                val inputSec = s.toString().toLongOrNull()
                if (inputSec != null && inputSec in 30..600) {
                    sampleIntervalSeconds = inputSec
                    if (sbSingleInterval.progress != inputSec.toInt()) {
                        sbSingleInterval.progress = inputSec.toInt()
                    }
                    resetAutoPowerSaveTimer()
                }
            }
        })
    }

    /**
     * 🌟 省電模式切換控制（同步靜音與喚醒恢復音效）
     */
    private fun enterPowerSaveMode() {
        layoutPowerSaveOverlay.visibility = View.VISIBLE

        // 1. 降低螢幕亮度至最低 (1%)
        val layoutParams = window.attributes
        layoutParams.screenBrightness = 0.01f
        window.attributes = layoutParams

        // 2. 🔇 關閉背景音樂與風聲，達到極致省電與靜音掛機
        SoundManager.stopBGM()
        SoundManager.stopWind()
        windHandler.removeCallbacks(windRunnable)
    }

    private fun exitPowerSaveMode() {
        layoutPowerSaveOverlay.visibility = View.GONE

        // 1. 恢復正常螢幕亮度
        val layoutParams = window.attributes
        layoutParams.screenBrightness = WindowManager.LayoutParams.BRIGHTNESS_OVERRIDE_NONE
        window.attributes = layoutParams

        // 2. 🎵 喚醒時恢復背景音樂
        SoundManager.startBGM()

        resetAutoPowerSaveTimer()
    }

    private fun resetAutoPowerSaveTimer() {
        powerSaveHandler.removeCallbacks(autoPowerSaveRunnable)
        powerSaveHandler.postDelayed(autoPowerSaveRunnable, 30_000) // 30 秒無操作自動暗屏
    }

    /**
     * 🌟 相機啟動與生命週期
     */
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

    /**
     * 🌟 影格分發給單植物策略處理
     */
    private fun processFrame(image: ImageProxy) {
        val isSingleMode = rgMode.checkedRadioButtonId == R.id.rbSingleMode
        if (isSingleMode) {
            singleStrategy.processFrame(image, isMonitoring, sampleIntervalSeconds)
        } else {
            // 多植物模式預留點
            image.close()
        }
    }

    /**
     * 🌟 更新 APP 畫面診斷文字與命中數（不彈出額外病害警告 UI）
     */
    fun updateDiagnosisUI(diagnosisName: String, streak: Int) {
        tvDiagnosis.text = "最新診斷：$diagnosisName"
        tvStreak.text = "連續命中數：$streak / 3"
    }

    /**
     * 🌟 Android 手機系統通知發送（頂部下拉通知列）
     */
    fun sendAlertNotification(diagnosisName: String) {
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

        notificationManager.notify(1001, notification)
    }

    /**
     * 🌟 生命週期管理：主題染色、音樂與風聲
     */
    override fun onResume() {
        super.onResume()
        resetAutoPowerSaveTimer()

        // 1. 套用 ThemeManager 動態主題
        ThemeManager.applyTheme(
            context = this,
            rootLayout = webcamRoot,
            mainButtons = listOf(btnToggleMonitor, btnAddRegion),
            titles = listOf(tvStatus, tvDiagnosis),
            imageButtons = listOf(btnPowerSave)
        )

        // 2. 播放背景音樂（若不在省電狀態下）
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
        powerSaveHandler.removeCallbacks(autoPowerSaveRunnable)
    }

    override fun onStop() {
        super.onStop()
        SoundManager.stopWind()
        windHandler.removeCallbacks(windRunnable)
    }

    override fun onDestroy() {
        super.onDestroy()
        powerSaveHandler.removeCallbacksAndMessages(null)
        windHandler.removeCallbacksAndMessages(null)
        cameraExecutor.shutdown()
    }
}