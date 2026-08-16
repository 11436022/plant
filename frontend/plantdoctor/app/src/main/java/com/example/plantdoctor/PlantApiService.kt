package com.example.plantdoctor

import android.content.Context
import com.google.gson.annotations.SerializedName
import okhttp3.MultipartBody
import okhttp3.OkHttpClient
import retrofit2.Call
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import retrofit2.http.*
import java.util.concurrent.TimeUnit

// ==========================================
// 1. Data Models (完全相容你原本 Activity 的欄位命名)
// ==========================================

data class LoginRequest(val username: String, val password: String)
// --- Auth & Account ---
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
    val full_name: String? = null
)

data class ForgotPasswordRequest(val email: String)
data class EmailVerificationRequest(val email: String)

data class GenericResponse(
    val status: String,
    val message: String?
)

// --- Predict (第一階段預測) ---
data class PredictionResponse(
    val prediction_id: String,
    val analysis_result: AnalysisResult,
    val metadata: Map<String, Any>? = null
)

data class AnalysisResult(
    val crop_name: String?,
    val status_name: String?,
    val category: String? = null,
    val confidence: Double?,
    val suggestion: String?,
    val treatment: String?
)

// --- Confirm (第二階段確認寫入日記) ---
// 相容你原本 ResultActivity 傳入的 disease_name 與 gemini_advice，後端忽略即可
data class DiaryConfirmRequest(
    val user_note: String? = null,
    val disease_name: String? = null,
    val gemini_advice: String? = null
)


data class DiaryConfirmData(
    val id: Int,
    val crop_name: String,
    val status_name: String,
    val confidence: Double?,
    val image_url: String,
    val suggestion: String?,
    val treatment: String?
)

data class DiaryConfirmResponse(
    val status: String,
    val message: String,
    val data: DiaryConfirmData?
)

// --- History & Diary (修改日記) ---
data class PatchDiaryRequest(
    val crop_name: String? = null,
    val status_name: String? = null,
    val user_note: String? = null,
    val user_corrected_status: String? = null
)

data class HistoryResponse(
    val status: String,
    val count: Int,
    val data: List<HistoryItem>
)

data class DetailDetailResponse(
    val status: String,
    val data: HistoryItem
)

// --- Knowledge (知識庫) ---
data class DiagnosisItem(
    val name: String,
    val category: String
)

data class DiagnosesResponse(
    val status: String,
    val count: Int,
    val data: List<DiagnosisItem>
)

// --- Webcam (即時監控與警報) ---
data class WebcamSettingsResponse(
    val sample_interval_seconds: Int,
    val alert_confidence: Double,
    val required_matches: Int,
    val cooldown_seconds: Int,
    val max_image_bytes: Long
)

// --- User Profile ---
data class UserProfileData(
    val username: String,
    val email: String?,
    val created_at: String
)

data class UserProfileResponse(
    val status: String,
    val data: UserProfileData
)


// --- Diagnosis Feedback ---
data class DiagnosisFeedbackRequest(
    val prediction_id: String, // <-- 改為傳送 prediction_id
    val original_plant_name: String?,
    val original_disease_name: String?,
    val is_plant_error: Boolean,
    val is_disease_error: Boolean
)

data class DiagnosisFeedbackResponse(
    val id: Int,
    val message: String
)

// --- 天氣相關 Data Models ---
data class WeatherData(
    val location: String,
    val weather: String,
    val temperature: String,
    val rain_probability: String,
    val update_time: String
)

data class PlantCareAdvice(
    val location: String,
    val current_weather: WeatherData,
    val watering_advice: String,
    val disease_prevention_advice: String,
    val general_care: String
)


// --- 2. API 接口定義 ---
data class WebcamMonitoringState(
    val streak: Int,
    val triggered: Boolean,
    val status: String
)

data class WebcamAlertItem(
    val id: Int,
    val user_id: Int,
    val crop_name: String?,
    val status_name: String?,
    val confidence: Double?,
    val image_url: String,
    val consecutive_matches: Int,
    val created_at: String,
    val acknowledged_at: String?
)

data class WebcamAnalyzeResponse(
    val status: String,
    val diagnosis: AnalysisResult,
    val monitoring: WebcamMonitoringState,
    val alert: WebcamAlertItem?
)

data class WebcamAlertListResponse(
    val status: String,
    val count: Int,
    val data: List<WebcamAlertItem>
)


// ==========================================
// 2. API 接口定義
// ==========================================

interface PlantApiService {

    // --- 【帳戶相關】 ---

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

    @POST("auth/user/verify-email/request")
    fun requestEmailVerification(@Body request: EmailVerificationRequest): Call<GenericResponse>

    @POST("auth/user/reset-password")
    fun resetPassword(@Body request: ResetPasswordRequest): Call<GenericResponse>


    // --- 【兩階段診斷與日記】 ---

    @Multipart
    @POST("predict/")
    fun predictImage(
        @Part file: MultipartBody.Part
    ): Call<PredictionResponse>

    @POST("diaries/confirm/{prediction_id}")
    fun confirmDiary(
        @Path("prediction_id") predictionId: String,
        @Body request: DiaryConfirmRequest = DiaryConfirmRequest()
    ): Call<DiaryConfirmResponse>

    @GET("diaries")
    fun getAllHistory(): Call<HistoryResponse>

    @GET("diaries/{diary_id}")
    fun getDiaryDetail(@Path("diary_id") diaryId: Int): Call<DetailDetailResponse>

    @DELETE("diaries/{diary_id}")
    fun deleteDiary(@Path("diary_id") diaryId: Int): Call<GenericResponse>

    @PATCH("diaries/{diary_id}")
    fun patchDiary(
        @Path("diary_id") diaryId: Int,
        @Body request: PatchDiaryRequest
    ): Call<GenericResponse>

    @GET("knowledge/diagnoses")
    fun getDiagnoses(): Call<DiagnosesResponse>

    @GET("auth/user/me")
    fun getUserProfile(): Call<UserProfileResponse>

    @POST("feedback/diagnosis")
    fun sendDiagnosisFeedback(@Body feedbackRequest: DiagnosisFeedbackRequest): Call<DiagnosisFeedbackResponse>


    // --- 【Webcam 即時監控與警報】 ---

    @GET("webcam/settings")
    fun getWebcamSettings(): Call<WebcamSettingsResponse>

    @Multipart
    @POST("webcam/analyze")
    fun analyzeWebcamFrame(
        @Part file: MultipartBody.Part
    ): Call<WebcamAnalyzeResponse>

    @GET("webcam/alerts")
    fun getWebcamAlerts(
        @Query("limit") limit: Int = 50,
        @Query("unacknowledged_only") unacknowledgedOnly: Boolean = false
    ): Call<WebcamAlertListResponse>

    @PATCH("webcam/alerts/{alert_id}/acknowledge")
    fun acknowledgeWebcamAlert(
        @Path("alert_id") alertId: Int
    ): Call<GenericResponse>

    @DELETE("webcam/alerts/{alert_id}")
    fun deleteWebcamAlert(
        @Path("alert_id") alertId: Int
    ): Call<GenericResponse>


    // --- 天氣相關API ---
    @GET("weather/cities")
    fun getTaiwanCities(): Call<List<String>>

    @GET("weather/current")
    fun getCurrentWeather(@Query("city") city: String): Call<WeatherData>

    @GET("weather/plant-care-advice")
    fun getPlantCareAdvice(@Query("city") city: String): Call<PlantCareAdvice>


    // --- 3. Retrofit 實例產生器 ---
    companion object {
        private val WIFI_HOST = BuildConfig.WIFI_HOST

        // 🌟 全域變數，用來即時同步目前能通的 IP 門牌
        var currentRunningIp: String = WIFI_HOST

        private fun getSmartBaseUrl(): String {
            val isEmulator = android.os.Build.FINGERPRINT.startsWith("generic")
                    || android.os.Build.MODEL.contains("google_sdk")
                    || android.os.Build.HARDWARE.contains("goldfish")
                    || android.os.Build.HARDWARE.contains("ranchu")

            if (isEmulator) {
                currentRunningIp = "10.0.2.2" // 🤖 模擬器
                return "http://10.0.2.2:8000/api/v1/"
            }

            return try {
                var isUsbConnected = false
                val thread = Thread {
                    try {
                        val socket = java.net.Socket()
                        socket.connect(java.net.InetSocketAddress("127.0.0.1", 8000), 200)
                        socket.close()
                        isUsbConnected = true
                    } catch (e: Exception) {
                        isUsbConnected = false
                    }
                }
                thread.start()
                thread.join(250)

                if (isUsbConnected) {
                    currentRunningIp = "127.0.0.1" // 🔌 有線插線
                    "http://127.0.0.1:8000/api/v1/"
                } else {
                    currentRunningIp = WIFI_HOST // 📱 無線區網
                    "http://$WIFI_HOST:8000/api/v1/"
                }
            } catch (e: Exception) {
                currentRunningIp = WIFI_HOST
                "http://$WIFI_HOST:8000/api/v1/"
            }
        }

        fun create(token: String? = null): PlantApiService {
            val dynamicBaseUrl = getSmartBaseUrl()
            android.util.Log.d(
                "PlantApi",
                "🚀 目前連線通道與 IP 鎖定: $dynamicBaseUrl, 圖片對齊 IP: $currentRunningIp"
            )

            val okHttpClient = OkHttpClient.Builder()
                .connectTimeout(30, TimeUnit.SECONDS)
                .readTimeout(60, TimeUnit.SECONDS)
                .addInterceptor(AuthInterceptor(token))
                .build()

            return Retrofit.Builder()
                .baseUrl(dynamicBaseUrl)
                .client(okHttpClient)
                .addConverterFactory(GsonConverterFactory.create())
                .build()
                .create(PlantApiService::class.java)
        }
    }
}