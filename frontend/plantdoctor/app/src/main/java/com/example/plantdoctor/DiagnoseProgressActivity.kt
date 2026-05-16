package com.example.plantdoctor

import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.view.MotionEvent
import android.util.Log
import android.widget.ProgressBar
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
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

    // 🌟 1. 建立風聲延遲計時器與任務（放在 onCreate 外面）
    private val windHandler = Handler(Looper.getMainLooper())
    private val windRunnable = Runnable {
        SoundManager.startWind() // 當按住滿 0.5 秒，正式吹起風聲
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_diagnose_progress)

        val progressBar = findViewById<ProgressBar>(R.id.progressBar_horizontal)
        val tvPercent = findViewById<TextView>(R.id.tv_percent)

        imageUriString = intent.getStringExtra("IMAGE_URI") ?: ""

        if (imageUriString.isEmpty()) {
            Toast.makeText(this, "找不到圖片資料", Toast.LENGTH_SHORT).show()
            finish()
            return
        }

        val imageUri = Uri.parse(imageUriString)
        uploadAndDiagnose(imageUri, progressBar, tvPercent)
    }

    private fun uploadAndDiagnose(uri: Uri, progressBar: ProgressBar, tvPercent: TextView) {
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
                if (response.isSuccessful) {
                    progressBar.progress = 100
                    tvPercent.text = "100%"

                    val predictionResult = response.body()
                    if (predictionResult != null) {
                        Toast.makeText(this@DiagnoseProgressActivity, "分析完成！", Toast.LENGTH_SHORT).show()

                        val predictionId = predictionResult.prediction_id
                        val analysisResult = predictionResult.analysis_result
                        val resultJson = Gson().toJson(analysisResult)

                        Log.d("DEBUG_JSON", "Passing to ResultActivity: $resultJson")
                        Log.d("DEBUG_ID", "Passing Prediction ID: $predictionId")

                        val intent = Intent(this@DiagnoseProgressActivity, ResultActivity::class.java)
                        intent.putExtra("IMAGE_URI", imageUriString)
                        intent.putExtra("PREDICTION_ID", predictionId)
                        intent.putExtra("ANALYSIS_RESULT_JSON", resultJson)
                        startActivity(intent)
                        finish()
                    } else {
                        Log.e("UploadError", "Response successful but body is null. Code: ${response.code()}")
                        Toast.makeText(this@DiagnoseProgressActivity, "分析失敗：伺服器回傳資料為空", Toast.LENGTH_LONG).show()
                        finish()
                    }
                } else {
                    Log.e("UploadError", "Code: ${response.code()}, Message: ${response.message()}")
                    Toast.makeText(this@DiagnoseProgressActivity, "分析失敗: ${response.code()}", Toast.LENGTH_LONG).show()
                    finish()
                }
            }

            override fun onFailure(call: Call<PredictionResponse>, t: Throwable) {
                Log.e("UploadError", t.message ?: "Unknown error")
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

    // 🌟 2. 核心修改：全螢幕長按雷達，判定長按 0.5 秒才吹風
    override fun onTouchEvent(event: MotionEvent?): Boolean {
        if (event != null) {
            when (event.action) {
                MotionEvent.ACTION_DOWN -> {
                    // 手指一碰到螢幕任意處：先設定一個 0.5 秒後的鬧鐘
                    windHandler.postDelayed(windRunnable, 500)
                }
                MotionEvent.ACTION_UP, MotionEvent.ACTION_CANCEL -> {
                    // 手指一離開或滑開螢幕：撤銷鬧鐘，停止風聲
                    windHandler.removeCallbacks(windRunnable)
                    SoundManager.stopWind()
                }
            }
        }
        return super.onTouchEvent(event)
    }

    // 🌟 3. 核心修改：離開畫面時（例如分析完自動跳轉時），安全切斷風聲並復原計時器
    override fun onStop() {
        super.onStop()
        SoundManager.stopWind()
        windHandler.removeCallbacks(windRunnable)
    }

    // 🌟 4. 銷毀畫面時清空計時器，防止記憶體洩漏
    override fun onDestroy() {
        super.onDestroy()
        windHandler.removeCallbacksAndMessages(null)
    }
}