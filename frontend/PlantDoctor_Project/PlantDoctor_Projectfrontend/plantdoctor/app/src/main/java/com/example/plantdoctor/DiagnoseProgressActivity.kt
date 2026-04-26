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

        // 2. 準備圖片檔案
        val file = uriToFile(uri)
        val requestFile = file.asRequestBody("image/*".toMediaTypeOrNull())
        val body = MultipartBody.Part.createFormData("file", file.name, requestFile)

        // 3. 發動網路請求
        val apiService = PlantApiService.create()

        // 這裡維持使用 ResponseBody 接收，但我們在成功後手動解析它
        apiService.uploadImage(token, body).enqueue(object : Callback<ResponseBody> {
            override fun onResponse(call: Call<ResponseBody>, response: Response<ResponseBody>) {
                if (response.isSuccessful) {
                    progressBar.progress = 100
                    tvPercent.text = "100%"

                    // --- 核心修正：解析並傳遞真實資料 ---
                    val responseString = response.body()?.string()

                    try {
                        // 使用 Gson 解析 JSON (這裡對應夥伴寫的 HistoryResponse 格式)
                        // 因為診斷回傳的單筆格式跟歷史紀錄的 data 列表解析邏輯相似
                        // 為了保險，我們直接傳送原始 JSON 字串給下一頁處理

                        Toast.makeText(this@DiagnoseProgressActivity, "辨識成功！", Toast.LENGTH_SHORT).show()

                        val intent = Intent(this@DiagnoseProgressActivity, ResultActivity::class.java)
                        intent.putExtra("DIAGNOSIS_RESULT", responseString) // 把整串結果丟給 ResultActivity
                        startActivity(intent)
                        finish()

                    } catch (e: Exception) {
                        Log.e("ParseError", "解析失敗: ${e.message}")
                        Toast.makeText(this@DiagnoseProgressActivity, "解析結果出錯", Toast.LENGTH_SHORT).show()
                        finish()
                    }
                    // ---------------------------------
                } else {
                    val errorJson = response.errorBody()?.string()
                    Log.e("ServerResponse", "Code: ${response.code()}, Error: $errorJson")

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
        val file = File(cacheDir, "${System.currentTimeMillis()}.jpg")
        val outputStream = FileOutputStream(file)
        inputStream?.copyTo(outputStream)
        outputStream.close()
        inputStream?.close()
        return file
    }
}