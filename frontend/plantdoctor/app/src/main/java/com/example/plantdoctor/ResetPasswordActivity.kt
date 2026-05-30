package com.example.plantdoctor

import android.os.Bundle
import android.widget.Button
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import com.google.android.material.textfield.TextInputEditText
import retrofit2.Call
import retrofit2.Callback
import retrofit2.Response
import com.example.plantdoctor.R


class ResetPasswordActivity : AppCompatActivity() {

    private lateinit var etNewPassword: TextInputEditText
    private lateinit var etConfirmPassword: TextInputEditText
    private lateinit var btnResetPassword: Button

    private var token: String? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_reset_password)

        // 初始化 UI 元件
        etNewPassword = findViewById<TextInputEditText>(R.id.etNewPassword)
        etConfirmPassword = findViewById<TextInputEditText>(R.id.etConfirmPassword)
        btnResetPassword = findViewById<Button>(R.id.btnResetPassword)

        // 從 Intent 的 Deep Link 中獲取 token
        val receivedToken = intent.data?.getQueryParameter("token")
        if (!receivedToken.isNullOrEmpty()) {
            token = receivedToken
        } else {
            Toast.makeText(this, "無效的重設連結，請重新操作", Toast.LENGTH_LONG).show()
            finish() // 如果沒有 token，直接關閉頁面
            return
        }

        // 設定按鈕點擊監聽器
        btnResetPassword.setOnClickListener {
            handleResetPassword()
        }
    }

    private fun handleResetPassword() {
        val newPassword = etNewPassword.text.toString().trim()
        val confirmPassword = etConfirmPassword.text.toString().trim()

        if (newPassword.isEmpty() || confirmPassword.isEmpty()) {
            Toast.makeText(this, "密碼不能為空", Toast.LENGTH_SHORT).show()
            return
        }

        if (newPassword != confirmPassword) {
            Toast.makeText(this, "兩次輸入的密碼不一致", Toast.LENGTH_SHORT).show()
            return
        }

        if (token.isNullOrEmpty()) {
            Toast.makeText(this, "缺少重設權杖，請透過郵件連結進入", Toast.LENGTH_LONG).show()
            return
        }

        // 建立請求物件
        val request = ResetPasswordRequest(
            token = token!!,
            newPassword = newPassword,
            confirmPassword = confirmPassword
        )

        // 呼叫 API
        val apiService = PlantApiService.create(null)
        apiService.resetPassword(request).enqueue(object : Callback<GenericResponse> {
            override fun onResponse(call: Call<GenericResponse>, response: Response<GenericResponse>) {
                if (response.isSuccessful) {
                    Toast.makeText(this@ResetPasswordActivity, "密碼重設成功！請用新密碼登入。", Toast.LENGTH_LONG).show()
                    // TODO: 可以引導使用者回到登入頁面
                    finish() // 關閉此頁面
                } else {
                    val errorBody = response.errorBody()?.string() ?: "未知錯誤"
                    Toast.makeText(this@ResetPasswordActivity, "密碼重設失敗: $errorBody", Toast.LENGTH_LONG).show()
                }
            }

            override fun onFailure(call: Call<GenericResponse>, t: Throwable) {
                Toast.makeText(this@ResetPasswordActivity, "網路連線失敗: ${t.message}", Toast.LENGTH_SHORT).show()
            }
        })
    }
}