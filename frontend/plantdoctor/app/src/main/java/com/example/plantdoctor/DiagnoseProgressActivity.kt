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
import okhttp3.RequestBody.Companion.toRequestBody
import okhttp3.RequestBody.Companion.asRequestBody
import retrofit2.Call
import retrofit2.Callback
import retrofit2.Response
import java.io.File
import java.io.FileOutputStream

class DiagnoseProgressActivity : AppCompatActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_diagnose_progress)

        val progressBar = findViewById<ProgressBar>(R.id.progressBar_horizontal)
        val tvPercent = findViewById<TextView>(R.id.tv_percent)

        val imageUriString = intent.getStringExtra("IMAGE_URI")

        if (imageUriString == null) {
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

        // 對應後端的 "user_note" 欄位 (傳空字串或自定義備註)
        val userNote = "".toRequestBody("text/plain".toMediaTypeOrNull())

        // 3. 使用自動化的 API Service (傳入 token)
        val apiService = PlantApiService.create(token)

        // 修改為直接接收 UploadResponse
        apiService.uploadImage(userNote, imagePart).enqueue(object : Callback<UploadResponse> {
            override fun onResponse(call: Call<UploadResponse>, response: Response<UploadResponse>) {
                if (response.isSuccessful) {
                    progressBar.progress = 100
                    tvPercent.text = "100%"

                    val result = response.body()
                    if (result != null && result.status == "success") {
                        Toast.makeText(this@DiagnoseProgressActivity, "辨識成功！", Toast.LENGTH_SHORT).show()

                        // 將診斷結果 (HistoryItem) 轉為 JSON 傳給下一頁
                        val resultJson = Gson().toJson(result.data)

                        val intent = Intent(this@DiagnoseProgressActivity, ResultActivity::class.java)
                        intent.putExtra("DIAGNOSIS_RESULT", resultJson)
                        startActivity(intent)
                        finish()
                    }
                } else {
                    Log.e("UploadError", "Code: ${response.code()}")
                    Toast.makeText(this@DiagnoseProgressActivity, "分析失敗: ${response.code()}", Toast.LENGTH_LONG).show()
                    finish()
                }
            }

            override fun onFailure(call: Call<UploadResponse>, t: Throwable) {
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