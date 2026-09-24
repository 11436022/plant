package com.example.plantdoctor

import android.util.Log
import okhttp3.Interceptor
import okhttp3.Response

class AuthInterceptor(private val token: String?) : Interceptor {
    override fun intercept(chain: Interceptor.Chain): Response {
        val originalRequest = chain.request()
        val urlPath = originalRequest.url.encodedPath

        Log.d("TOKEN_CHECK", "========================================")
        Log.d("TOKEN_CHECK", "📡 準備發送 Request 到: $urlPath")

        // 1. 如果完全沒有 Token (null 或空字串)
        if (token.isNullOrEmpty()) {
            Log.e("TOKEN_CHECK", "❌ 警告！傳入 AuthInterceptor 的 token 為 NULL 或空字串！")
            Log.e("TOKEN_CHECK", "⚠️ 此 Request ($urlPath) 將不會帶上 Authorization Header發送！")
            Log.d("TOKEN_CHECK", "========================================")
            return chain.proceed(originalRequest)
        }

        // 2. 如果有 Token，檢查並確保帶上 Bearer 前綴
        val cleanToken = token.trim()
        val authHeaderValue = if (cleanToken.startsWith("Bearer ", ignoreCase = true)) {
            cleanToken
        } else {
            "Bearer $cleanToken"
        }

        Log.d("TOKEN_CHECK", "🔑 Token 狀態正常！長度: ${cleanToken.length}")
        Log.d("TOKEN_CHECK", "✅ 加入 Header: Authorization: ${authHeaderValue.take(20)}...")
        Log.d("TOKEN_CHECK", "========================================")

        val newRequest = originalRequest.newBuilder()
            .header("Authorization", authHeaderValue)
            .build()

        return chain.proceed(newRequest)
    }
}