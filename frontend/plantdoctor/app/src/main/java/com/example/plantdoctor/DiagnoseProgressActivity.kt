package com.example.plantdoctor

import android.content.Context
import android.content.Intent
import android.content.res.ColorStateList
import android.graphics.Color
import android.net.Uri
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.util.Log
import android.view.MotionEvent
import android.widget.ProgressBar
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.constraintlayout.widget.ConstraintLayout
import com.google.gson.Gson
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.asRequestBody
import retrofit2.Call
import retrofit2.Callback
import retrofit2.Response
import java.io.File
import java.io.FileOutputStream

class DiagnoseProgressActivity : AppCompatActivity() {

    private lateinit var imageUriString: String
    private lateinit var progressRoot: ConstraintLayout

    // 🌟 核心修復 1：宣告前後景兩層落葉 View 變數
    private lateinit var leavesBack: FallingLeavesView
    private lateinit var leavesFront: FallingLeavesView

    private lateinit var progressBar: ProgressBar
    private lateinit var tvPercent: TextView
    private lateinit var tvStatus: TextView

    // 風聲計時器
    private val windHandler = Handler(Looper.getMainLooper())
    private val windRunnable = Runnable {
        SoundManager.startWind()
    }

    // 假進度條模擬器
    private val progressHandler = Handler(Looper.getMainLooper())
    private var currentProgress = 0
    private var isApiFinished = false

    private val progressRunnable = object : Runnable {
        override fun run() {
            if (!isApiFinished && currentProgress < 90) {
                currentProgress += (1..3).random()
                if (currentProgress > 90) currentProgress = 90

                progressBar.progress = currentProgress
                tvPercent.text = "$currentProgress%"

                val nextDelay = (320..580).random().toLong()
                progressHandler.postDelayed(this, nextDelay)
            }
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_diagnose_progress)

        // 綁定 UI 元件
        progressRoot = findViewById(R.id.progress_root_layout)
        progressBar = findViewById(R.id.progressBar_horizontal)
        tvPercent = findViewById(R.id.tv_percent)
        tvStatus = findViewById(R.id.tv_progress_status)

        // 🌟 核心修復 2：綁定 XML 裡的前後景 ID，並指定層級模式
        leavesBack = findViewById(R.id.falling_leaves_back)
        leavesFront = findViewById(R.id.falling_leaves_front)

        leavesBack.drawLayerMode = FallingLeavesView.LayerMode.BACKGROUND_ONLY
        leavesFront.drawLayerMode = FallingLeavesView.LayerMode.FOREGROUND_ONLY

        // 初始化音效管理器
        SoundManager.init(this)

        // 召喚大總管換好背景與文字色彩
        ThemeManager.applyTheme(
            context = this,
            rootLayout = progressRoot,
            titles = listOf(tvPercent, tvStatus)
        )

        // 動態染進度條主題色
        val sharedPref = getSharedPreferences("PlantDoctor", Context.MODE_PRIVATE)
        val themeId = sharedPref.getInt("THEME_COLOR_ID", 0)
        val progressColorStr = when (themeId) {
            1 -> "#1565C0"
            2 -> "#D84315"
            3 -> "#AD1457"
            else -> "#2E7D32"
        }
        progressBar.progressTintList = ColorStateList.valueOf(Color.parseColor(progressColorStr))

        imageUriString = intent.getStringExtra("IMAGE_URI") ?: ""

        if (imageUriString.isEmpty()) {
            Toast.makeText(this, "找不到圖片資料", Toast.LENGTH_SHORT).show()
            finish()
            return
        }

        // 啟動進度條模擬
        progressHandler.post(progressRunnable)

        val imageUri = Uri.parse(imageUriString)
        uploadAndDiagnose(imageUri)
    }

    override fun onResume() {
        super.onResume()
        if (::progressRoot.isInitialized) {
            ThemeManager.applyTheme(
                context = this,
                rootLayout = progressRoot,
                titles = listOf(tvPercent, tvStatus)
            )
        }
        SoundManager.startBGM()
    }

    private fun uploadAndDiagnose(uri: Uri) {
        val sharedPref = getSharedPreferences("PlantDoctor", Context.MODE_PRIVATE)
        val token = sharedPref.getString("token", null)

        if (token == null) {
            startActivity(Intent(this, LoginActivity::class.java))
            finish()
            return
        }

        val file = uriToFile(uri)
        val requestFile = file.asRequestBody("image/*".toMediaTypeOrNull())
        val imagePart = MultipartBody.Part.createFormData("file", file.name, requestFile)

        val apiService = PlantApiService.create(token)

        apiService.predictImage(imagePart).enqueue(object : Callback<PredictionResponse> {
            override fun onResponse(call: Call<PredictionResponse>, response: Response<PredictionResponse>) {
                isApiFinished = true
                progressHandler.removeCallbacks(progressRunnable)

                if (response.isSuccessful) {
                    progressBar.progress = 100
                    tvPercent.text = "100%"

                    val predictionResult = response.body()
                    if (predictionResult != null) {
                        Toast.makeText(this@DiagnoseProgressActivity, "分析完成！", Toast.LENGTH_SHORT).show()

                        val predictionId = predictionResult.prediction_id
                        val analysisResult = predictionResult.analysis_result
                        val resultJson = Gson().toJson(analysisResult)

                        val intent = Intent(this@DiagnoseProgressActivity, ResultActivity::class.java)
                        intent.putExtra("IMAGE_URI", imageUriString)
                        intent.putExtra("PREDICTION_ID", predictionId)
                        intent.putExtra("ANALYSIS_RESULT_JSON", resultJson)
                        startActivity(intent)
                        finish()
                    } else {
                        Toast.makeText(this@DiagnoseProgressActivity, "分析失敗：伺服器回傳資料為空", Toast.LENGTH_LONG).show()
                        finish()
                    }
                } else {
                    Toast.makeText(this@DiagnoseProgressActivity, "分析失敗: ${response.code()}", Toast.LENGTH_LONG).show()
                    finish()
                }
            }

            override fun onFailure(call: Call<PredictionResponse>, t: Throwable) {
                isApiFinished = true
                progressHandler.removeCallbacks(progressRunnable)
                Toast.makeText(this@DiagnoseProgressActivity, "網路連線超時，請檢查伺服器", Toast.LENGTH_SHORT).show()
                finish()
            }
        })
    }

    private fun uriToFile(uri: Uri): File {
        val inputStream = contentResolver.openInputStream(uri)
        val file = File(cacheDir, "${System.currentTimeMillis()}.jpg")
        val outputStream = FileOutputStream(file)
        inputStream?.copyTo(outputStream)
        outputStream.close()
        inputStream?.close()
        return file
    }

    /**
     * 🌟 核心修復 3：分發觸控手勢給前後兩層落葉 View
     */
    override fun dispatchTouchEvent(ev: MotionEvent?): Boolean {
        if (ev != null) {
            if (::leavesBack.isInitialized) leavesBack.onTouchEventHandled(ev)
            if (::leavesFront.isInitialized) leavesFront.onTouchEventHandled(ev)

            when (ev.action) {
                MotionEvent.ACTION_DOWN -> {
                    windHandler.postDelayed(windRunnable, 500)
                }
                MotionEvent.ACTION_UP, MotionEvent.ACTION_CANCEL -> {
                    windHandler.removeCallbacks(windRunnable)
                    SoundManager.stopWind()
                }
            }
        }
        return super.dispatchTouchEvent(ev)
    }

    override fun onStop() {
        super.onStop()
        SoundManager.stopWind()
        windHandler.removeCallbacks(windRunnable)
        progressHandler.removeCallbacks(progressRunnable)
    }

    override fun onDestroy() {
        super.onDestroy()
        windHandler.removeCallbacksAndMessages(null)
        progressHandler.removeCallbacksAndMessages(null)
    }
}