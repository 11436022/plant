package com.example.plantdoctor

data class PlantSession(
    var id: String = System.currentTimeMillis().toString(),
    var name: String,
    val cropZones: MutableList<CropZone> = mutableListOf()
) {
    override fun toString(): String = name // 讓 Spinner 預設顯示組別名稱
}