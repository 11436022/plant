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
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.asRequestBody
import okhttp3.ResponseBody
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
        val cleanToken = intent.getStringExtra("CLEAN_TOKEN") // 從 UploadActivity 傳過來的乾淨 Token

        if (imageUriString == null) {
            Toast.makeText(this, "找不到圖片資料", Toast.LENGTH_SHORT).show()
            finish()
            return
        }

        val imageUri = Uri.parse(imageUriString)
        uploadAndDiagnose(imageUri, cleanToken, progressBar, tvPercent)
    }

    private fun uploadAndDiagnose(uri: Uri, passedToken: String?, progressBar: ProgressBar, tvPercent: TextView) {
        // 1. 優先使用傳過來的 Token，如果沒有則從 SharedPreferences 讀取
        val sharedPref = getSharedPreferences("PlantDoctor", Context.MODE_PRIVATE)
        val token = passedToken ?: sharedPref.getString("token", null)

        if (token == null) {
            Toast.makeText(this, "尚未登入，請先登入", Toast.LENGTH_SHORT).show()
            startActivity(Intent(this, LoginActivity::class.java))
            finish()
            return
        }

        // 2. 準備圖片檔案 (改用正確的 Part 名稱 "file" 對應後端)
        val file = uriToFile(uri)
        val requestFile = file.asRequestBody("image/*".toMediaTypeOrNull())
        // 注意：這裡的 "file" 必須跟 main.py 裡的 create_diary(file: UploadFile) 名稱一致
        val body = MultipartBody.Part.createFormData("file", file.name, requestFile)

        // 3. 發動網路請求
        val apiService = PlantApiService.create()

        // 重要修正：token 變數裡面已經包含 "Bearer " 了（登入時存入的）
        // 所以直接傳入 token 即可，不要寫成 "Bearer $token"
        apiService.uploadImage(token, body).enqueue(object : Callback<ResponseBody> {
            override fun onResponse(call: Call<ResponseBody>, response: Response<ResponseBody>) {
                if (response.isSuccessful) {
                    progressBar.progress = 100
                    tvPercent.text = "100%"

                    Toast.makeText(this@DiagnoseProgressActivity, "辨識成功！", Toast.LENGTH_SHORT).show()
                    val intent = Intent(this@DiagnoseProgressActivity, ResultActivity::class.java)
                    startActivity(intent)
                    finish()
                } else {
                    val errorJson = response.errorBody()?.string()
                    Log.e("ServerResponse", "Code: ${response.code()}, Error: $errorJson")

                    // 如果 401，通常是 Token 格式問題
                    if (response.code() == 401) {
                        Toast.makeText(this@DiagnoseProgressActivity, "驗證失敗，請重新登入", Toast.LENGTH_LONG).show()
                    } else {
                        Toast.makeText(this@DiagnoseProgressActivity, "分析失敗: ${response.code()}", Toast.LENGTH_LONG).show()
                    }
                    finish()
                }
            }

            override fun onFailure(call: Call<ResponseBody>, t: Throwable) {
                Log.e("UploadError", t.message ?: "Unknown error")
                Toast.makeText(this@DiagnoseProgressActivity, "連線失敗，請檢查網路", Toast.LENGTH_LONG).show()
                finish()
            }
        })
    }

    private fun uriToFile(uri: Uri): File {
        val inputStream = contentResolver.openInputStream(uri)
        val file = File(cacheDir, "${System.currentTimeMillis()}.jpg") // 使用時間戳避免衝突
        val outputStream = FileOutputStream(file)
        inputStream?.copyTo(outputStream)
        outputStream.close()
        inputStream?.close()
        return file
    }
}