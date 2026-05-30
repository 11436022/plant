package com.example.plantdoctor

import com.google.gson.annotations.SerializedName

data class ResetPasswordRequest(
    @SerializedName("token")
    val token: String,
    @SerializedName("new_password")
    val newPassword: String,
    @SerializedName("confirm_password")
    val confirmPassword: String
)