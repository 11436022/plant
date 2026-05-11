package com.example.plantdoctor

import okhttp3.MultipartBody
import okhttp3.OkHttpClient
import okhttp3.RequestBody
import retrofit2.Call
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import retrofit2.http.*
import java.util.concurrent.TimeUnit

// --- 1. Data Models (對應後端 JSON 結構) ---

// 登入與註冊
data class LoginRequest(val username: String, val password: String)
data class LoginResponse(
    val status: String,
    val message: String,
    val access_token: String,
    val token_type: String,
    val email: String?
)

data class RegisterRequest(
    val username: String,
    val password: String,
    val email: String,
    val full_name: String
)

// 忘記密碼
data class ForgotPasswordRequest(val email: String)

// 診斷紀錄相關 (共用 HistoryItem)
data class UploadResponse(val status: String, val data: HistoryItem)

data class HistoryResponse(
    val status: String,
    val count: Int,
    val data: List<HistoryItem>
)

data class DetailDetailResponse(val status: String, val data: HistoryItem)

// 通用回傳 (用於註冊成功、刪除成功、忘記密碼成功等)
data class GenericResponse(val status: String, val message: String)


// --- 2. API 接口定義 ---

interface PlantApiService {

    // 【帳戶相關】
    @POST("users/register")
    fun register(@Body request: RegisterRequest): Call<GenericResponse>

    @POST("user/login")
    fun login(@Body request: LoginRequest): Call<LoginResponse>

    @POST("user/forgot-password")
    fun forgotPassword(@Body request: ForgotPasswordRequest): Call<GenericResponse>

    // 【診斷日誌相關】 (注意：這些會自動由 Interceptor 加上 Token)

    @Multipart
    @POST("diaries/upload")
    fun uploadImage(
        @Part("user_note") userNote: RequestBody,
        @Part image: MultipartBody.Part
    ): Call<UploadResponse>

    @GET("diaries")
    fun getAllHistory(): Call<HistoryResponse>

    @GET("diaries/{diary_id}")
    fun getDiaryDetail(@Path("diary_id") diaryId: Int): Call<DetailDetailResponse>

    @DELETE("diaries/{diary_id}")
    fun deleteDiary(@Path("diary_id") diaryId: Int): Call<GenericResponse>


    // --- 3. Retrofit 實例產生器 ---
    companion object {
        // 模擬器連線本機電腦後端的專用 IP
        private const val BASE_URL = "http://10.0.2.2:8000/"

        fun create(token: String? = null): PlantApiService {

            // 建立 OkHttpClient，配置自動蓋章攔截器與超時設定
            val okHttpClient = OkHttpClient.Builder()
                .connectTimeout(30, TimeUnit.SECONDS) // 連線超時
                .readTimeout(60, TimeUnit.SECONDS)    // 讀取超時 (給 AI 診斷留時間)
                .addInterceptor(AuthInterceptor(token)) // 注入攔截器
                .build()

            return Retrofit.Builder()
                .baseUrl(BASE_URL)
                .client(okHttpClient)
                .addConverterFactory(GsonConverterFactory.create())
                .build()
                .create(PlantApiService::class.java)
        }
    }
}