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
// data class UploadResponse(val status: String, val data: HistoryItem) // <--- 舊的上傳回傳，將被取代

// 【新流程】兩階段提交的資料模型
data class PredictionResponse(
    val prediction_id: String,
    val analysis_result: AnalysisResult
)
data class AnalysisResult(
    val crop_name: String?,
    val category: String?,
    val status_name: String?,
    val confidence: Double?,
    val suggestion: String?,
    val treatment: String?
)
data class ConfirmRequest(val user_note: String)


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
    @POST("auth/users/register")
    fun register(@Body request: RegisterRequest): Call<GenericResponse>

    @FormUrlEncoded
    @POST("auth/login")
    fun login(
        @Field("username") username: String,
        @Field("password") password: String
    ): Call<LoginResponse>

    @POST("auth/user/forgot-password")
    fun forgotPassword(@Body request: ForgotPasswordRequest): Call<GenericResponse>

    // 【診斷日誌相關】 (注意：這些會自動由 Interceptor 加上 Token)

    // @Multipart
    // @POST("diaries/upload")
    // fun uploadImage(
    //     @Part("user_note") userNote: RequestBody,
    //     @Part image: MultipartBody.Part
    // ): Call<UploadResponse>

    // --- 新的兩階段提交流程 ---

    // 1. 預測 API
    @Multipart
    @POST("predict/") // 注意路徑變為 /api/v1/predict/
    fun predictImage(
        @Part image: MultipartBody.Part
    ): Call<PredictionResponse>

    // 2. 確認儲存 API
    @POST("diaries/confirm/{prediction_id}")
    fun confirmDiary(
        @Path("prediction_id") predictionId: String,
        @Body request: ConfirmRequest
    ): Call<GenericResponse> // 假設成功只回傳通用訊息


    @GET("diaries")
    fun getAllHistory(): Call<HistoryResponse>

    @GET("diaries/{diary_id}")
    fun getDiaryDetail(@Path("diary_id") diaryId: Int): Call<DetailDetailResponse>

    @DELETE("diaries/{diary_id}")
    fun deleteDiary(@Path("diary_id") diaryId: Int): Call<GenericResponse>


    // --- 3. Retrofit 實例產生器 ---
    companion object {
        // 模擬器連線本機電腦後端的專用 IP，並包含 API 版本
        private const val BASE_URL = "http://10.0.2.2:8000/api/v1/"

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