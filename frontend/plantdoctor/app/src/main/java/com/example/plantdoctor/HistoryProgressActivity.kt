package com.example.plantdoctor

import android.content.Context
import android.content.Intent
import android.os.Bundle
import android.util.Log
import android.widget.ProgressBar
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import com.google.gson.Gson
import retrofit2.Call
import retrofit2.Callback
import retrofit2.Response

class HistoryProgressActivity : AppCompatActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_history_progress)

        val progressBar = findViewById<ProgressBar>(R.id.progressBar_history)

        // 1. 從小本本拿 Token
        val sharedPref = getSharedPreferences("PlantDoctor", Context.MODE_PRIVATE)
        val token = sharedPref.getString("token", null)

        if (token == null) {
            Toast.makeText(this, "登入已失效", Toast.LENGTH_SHORT).show()
            startActivity(Intent(this, LoginActivity::class.java))
            finish()
            return
        }

        // 2. 真的去拿歷史紀錄
        fetchHistoryAndNavigate(token, progressBar)
    }

    private fun fetchHistoryAndNavigate(token: String, progressBar: ProgressBar) {
        val apiService = PlantApiService.create(token)

        apiService.getAllHistory().enqueue(object : Callback<HistoryResponse> {
            override fun onResponse(call: Call<HistoryResponse>, response: Response<HistoryResponse>) {
                if (response.isSuccessful) {
                    progressBar.progress = 100

                    // 把拿到的資料轉成 JSON 傳給下一頁，省去下一頁再跑一次網路請求的時間
                    val historyDataJson = Gson().toJson(response.body()?.data)

                    val intent = Intent(this@HistoryProgressActivity, HistoryListActivity::class.java)
                    intent.putExtra("HISTORY_DATA", historyDataJson)
                    startActivity(intent)
                    finish()
                } else {
                    Log.e("HistoryProgress", "Error: ${response.code()}")
                    Toast.makeText(this@HistoryProgressActivity, "獲取紀錄失敗", Toast.LENGTH_SHORT).show()
                    finish()
                }
            }

            override fun onFailure(call: Call<HistoryResponse>, t: Throwable) {
                Log.e("HistoryProgress", "Failure: ${t.message}")
                Toast.makeText(this@HistoryProgressActivity, "連線超時", Toast.LENGTH_SHORT).show()
                finish()
            }
        })
    }
}