package com.example.plantdoctor

import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.util.Log
import android.widget.ProgressBar
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import com.google.gson.Gson
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.asRequestBody
import okhttp3.RequestBody.Companion.toRequestBody
import retrofit2.Call
import retrofit2.Callback
import retrofit2.Response
import java.io.File
import java.io.FileOutputStream

class DiagnoseProgressActivity : AppCompatActivity() {

    private lateinit var imageUriString: String

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
        // 1. 從 SharedPreferences 拿原始 Token (Interceptor 會幫我們加 Bearer)
        val sharedPref = getSharedPreferences("PlantDoctor", Context.MODE_PRIVATE)
        val token = sharedPref.getString("token", null)

        if (token == null) {
            startActivity(Intent(this, LoginActivity::class.java))
            finish()
            return
        }

        // 2. 準備圖片檔案與參數
        val file = uriToFile(uri)
        val requestFile = file.asRequestBody("image/*".toMediaTypeOrNull())
        // 對應後端的 "file" 欄位
        val imagePart = MultipartBody.Part.createFormData("file", file.name, requestFile)

        // 3. 使用自動化的 API Service (傳入 token)
        val apiService = PlantApiService.create(token)

        // 【新流程】呼叫 predictImage API
        apiService.predictImage(imagePart).enqueue(object : Callback<PredictionResponse> {
            override fun onResponse(call: Call<PredictionResponse>, response: Response<PredictionResponse>) {
                if (response.isSuccessful) {
                    progressBar.progress = 100
                    tvPercent.text = "100%"

                    val predictionResult = response.body()
                    if (predictionResult != null) {
                        Toast.makeText(this@DiagnoseProgressActivity, "分析完成！", Toast.LENGTH_SHORT).show()

                        // 從回傳結果中，取出 prediction_id 和 analysis_result
                        val predictionId = predictionResult.prediction_id
                        val analysisResult = predictionResult.analysis_result

                        // 將 analysis_result 物件轉為 JSON 字串，方便傳遞
                        val resultJson = Gson().toJson(analysisResult)

                        // 【偵錯用】印出準備要傳送的資料
                        Log.d("DEBUG_JSON", "Passing to ResultActivity: $resultJson")
                        Log.d("DEBUG_ID", "Passing Prediction ID: $predictionId")

                        val intent = Intent(this@DiagnoseProgressActivity, ResultActivity::class.java)
                        // 將三份資料都放入 Intent
                        intent.putExtra("IMAGE_URI", imageUriString) // <-- 新增：傳遞圖片的本地路徑
                        intent.putExtra("PREDICTION_ID", predictionId)
                        intent.putExtra("ANALYSIS_RESULT_JSON", resultJson)
                        startActivity(intent)
                        finish()
                    } else {
                        // 這種情況通常是後端回傳了 200 OK，但 body 是空的
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
}