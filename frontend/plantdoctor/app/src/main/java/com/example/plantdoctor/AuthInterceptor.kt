package com.example.plantdoctor

import okhttp3.Interceptor
import okhttp3.Response

class AuthInterceptor(private val token: String?) : Interceptor {
    override fun intercept(chain: Interceptor.Chain): Response {
        val originalRequest = chain.request()

        // 如果沒有 Token，就直接發送原始請求（例如登入或註冊時）
        if (token.isNullOrEmpty()) {
            return chain.proceed(originalRequest)
        }

        // 如果有 Token，就幫 Request 加上 Authorization Header
        val newRequest = originalRequest.newBuilder()
            .header("Authorization", "Bearer $token")
            .build()

        return chain.proceed(newRequest)
    }
}