package com.example.plantdoctor

import okhttp3.MultipartBody
import okhttp3.ResponseBody
import retrofit2.Call
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import retrofit2.http.*

// --- 將 Request 定義放在這裡，全專案共用 ---
data class LoginRequest(val username: String, val password: String)
data class RegisterRequest(
    val username: String,
    val password: String,
    val email: String,
    val full_name: String,
    val role: String = "user"
)

data class HistoryResponse(
    val status: String,
    val count: Int,
    val data: List<HistoryItem> 
)

// 這是詳情的包裝
data class DetailDetailResponse(
    val status: String,
    val data: HistoryItem // 詳情只會回傳一筆資料
)

interface PlantApiService {

    // 1. 註冊帳戶
    @POST("users/register")
    fun register(@Body request: RegisterRequest): Call<ResponseBody>

    // 2. 帳戶登入
    @POST("user/login")
    fun login(@Body request: LoginRequest): Call<ResponseBody>

    // 3. 上傳照片
    @Multipart
    @POST("diaries/upload")
    fun uploadImage(
        @Header("Authorization") token: String,
        @Part image: MultipartBody.Part
    ): Call<ResponseBody>

    // 4. 取得所有紀錄清單 (Master)
    @GET("diaries")
    fun getAllHistory(
        @Header("Authorization") token: String
    ): Call<HistoryResponse>

    // 5. 取得單筆詳情 (Detail)
    @GET("diaries/{diary_id}")
    fun getDiaryDetail(
        @Path("diary_id") diaryId: Int,
        @Header("Authorization") token: String
    ): Call<DetailDetailResponse> // 對應單筆詳情的回傳

    companion object {
        private const val BASE_URL = "http://10.0.2.2:8000/"

        fun create(): PlantApiService {
            return Retrofit.Builder()
                .baseUrl(BASE_URL)
                .addConverterFactory(GsonConverterFactory.create())
                .build()
                .create(PlantApiService::class.java)
        }
    }
    
}