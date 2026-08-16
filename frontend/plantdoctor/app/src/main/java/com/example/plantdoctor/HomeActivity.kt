package com.example.plantdoctor

import android.Manifest
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.location.Geocoder
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.util.Log
import android.view.MotionEvent
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.cardview.widget.CardView
import androidx.constraintlayout.widget.ConstraintLayout
import androidx.core.app.ActivityCompat
import com.example.plantdoctor.PlantApiService
import com.example.plantdoctor.PlantCareAdvice
import com.getkeepsafe.taptargetview.TapTarget
import com.getkeepsafe.taptargetview.TapTargetSequence
import com.google.android.gms.location.FusedLocationProviderClient
import com.google.android.gms.location.LocationCallback
import com.google.android.gms.location.LocationRequest
import com.google.android.gms.location.LocationResult
import com.google.android.gms.location.LocationServices
import com.google.android.gms.location.Priority
import retrofit2.Call
import retrofit2.Callback
import retrofit2.Response
import java.util.Locale

class HomeActivity : AppCompatActivity() {

    private val windHandler = Handler(Looper.getMainLooper())
    private val windRunnable = Runnable {
        SoundManager.startWind()
    }

    private lateinit var homeRoot: ConstraintLayout
    private lateinit var cardDiagnose: CardView
    private lateinit var cardWebcam: CardView
    private lateinit var cardHistory: CardView
    private lateinit var cardSettings: CardView
    private lateinit var tvhomeTitle: TextView

    // 🌟 天氣建議相關 UI 元件
    private lateinit var tvWeatherLocation: TextView
    private lateinit var tvWeatherInfo: TextView
    private lateinit var tvWateringAdvice: TextView
    private lateinit var tvDiseaseAdvice: TextView
    private lateinit var tvGeneralCare: TextView

    private lateinit var fusedLocationClient: FusedLocationProviderClient
    private var locationCallback: LocationCallback? = null
    private val LOCATION_PERMISSION_REQUEST_CODE = 1001
    private var isLocationLoaded = false // 新增旗標，防止重複載入

    // 用於處理定位請求超時
    private val locationTimeoutHandler = Handler(Looper.getMainLooper())
    private var locationTimeoutRunnable: Runnable? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_home)

        // 1. 綁定元件
        homeRoot = findViewById(R.id.home_root_layout)
        cardDiagnose = findViewById(R.id.card_diagnose)
        cardWebcam = findViewById(R.id.card_webcam)
        cardHistory = findViewById(R.id.card_history)
        cardSettings = findViewById(R.id.card_settings)
        tvhomeTitle = findViewById(R.id.tv_home_title)
        // 🌟 綁定天氣資訊相關的 TextView (假設 ID 已在 activity_home.xml 中定義)
        tvWeatherLocation = findViewById(R.id.tv_weather_location)
        tvWeatherInfo = findViewById(R.id.tv_weather_info)
        tvWateringAdvice = findViewById(R.id.tv_watering_advice)
        tvDiseaseAdvice = findViewById(R.id.tv_disease_advice)
        tvGeneralCare = findViewById(R.id.tv_general_care)

        // 初始化定位服務客戶端
        fusedLocationClient = LocationServices.getFusedLocationProviderClient(this)

        // 3. 初始化音效管理器
        SoundManager.init(this)

        // 4. 設定按鈕點擊事件
        setupClickListeners()

        // 5. 載入天氣資訊 -> 移至 onStart()
        // requestLocationAndLoadWeather()

        // 🌟 檢查是否需要顯示主頁新手指引
        val sharedPref = getSharedPreferences("PlantDoctor", MODE_PRIVATE)
        val isFirstTime = sharedPref.getBoolean("IS_FIRST_TIME_HOME", true)

        if (isFirstTime) {
            showTutorial()
        }
    }

    override fun onStart() {
        super.onStart()
        // 只有在天氣尚未載入時，才開始定位流程
        if (!isLocationLoaded) {
            Log.d("LocationDebug", "onStart: Location not loaded, starting process.")
            // 讓天氣 UI 顯示載入中
            showLoadingState()
            requestLocationAndLoadWeather()
        } else {
            Log.d("LocationDebug", "onStart: Location already loaded, skipping.")
        }
    }

    override fun onResume() {
        super.onResume()

        // 🌟 核心新增：每次回到主頁時，強迫大總管重新載入最新主題背景與標題顏色！
        ThemeManager.applyTheme(this, homeRoot, titles = listOf(tvhomeTitle))

        // 重新載入音效設定 (假設 SoundManager 內部會處理)
        SoundManager.startBGM()
    }

    private fun showLoadingState() {
        tvWeatherLocation.text = "地點：載入中..."
        tvWeatherInfo.text = "天氣：載入中..."
        tvWateringAdvice.text = "澆水建議：載入中..."
        tvDiseaseAdvice.text = "病害預防：載入中..."
        tvGeneralCare.text = "一般照護：載入中..."
    }

    private fun setupClickListeners() {
        cardDiagnose.setOnClickListener {
            SoundManager.playBubblePop()
            val intent = Intent(this, UploadActivity::class.java)
            startActivity(intent)
        }

        cardWebcam.setOnClickListener {
            SoundManager.playBubblePop()
            val intent = Intent(this, WebcamActivity::class.java)
            startActivity(intent)
        }

        cardHistory.setOnClickListener {
            SoundManager.playBubblePop()
            val intent = Intent(this, HistoryListActivity::class.java)
            startActivity(intent)
        }

        cardSettings.setOnClickListener {
            SoundManager.playBubblePop()
            val intent = Intent(this, SettingsActivity::class.java)
            startActivity(intent)
        }
    }

    private fun requestLocationAndLoadWeather() {
        // 1. 檢查權限
        if (ActivityCompat.checkSelfPermission(
                this,
                Manifest.permission.ACCESS_FINE_LOCATION
            ) == PackageManager.PERMISSION_GRANTED
        ) {
            // 權限已授予，直接獲取位置
            getLastLocation()
        } else {
            // 權限未授予，發起請求
            ActivityCompat.requestPermissions(
                this,
                arrayOf(Manifest.permission.ACCESS_FINE_LOCATION),
                LOCATION_PERMISSION_REQUEST_CODE
            )
        }
    }

    private fun getLastLocation() {
        if (ActivityCompat.checkSelfPermission(
                this,
                Manifest.permission.ACCESS_FINE_LOCATION
            ) != PackageManager.PERMISSION_GRANTED
        ) {
            Log.w("LocationDebug", "getLastLocation: Permission check failed, should not happen.")
            loadWeatherForCity("臺北市") // 使用預設城市
            return
        }
        Log.d("LocationDebug", "getLastLocation: Attempting to get last location...")
        fusedLocationClient.lastLocation
            .addOnSuccessListener { location ->
                if (location != null) {
                    // 成功獲取最後位置，直接使用
                    Log.d("LocationDebug", "getLastLocation: Success! Got last known location.")
                    val city = getCityNameFromLocation(location.latitude, location.longitude)
                    loadWeatherForCity(city)
                } else {
                    // 最後位置為 null，啟動 Plan B：請求即時位置更新
                    Log.w("LocationDebug", "getLastLocation: Success, but last location is null. Requesting fresh location.")
                    requestFreshLocation()
                }
            }
            .addOnFailureListener { e ->
                // 獲取最後位置失敗，也啟動 Plan B
                Log.e("LocationDebug", "getLastLocation: Failed to get last location.", e)
                requestFreshLocation()
            }
    }

    private fun requestFreshLocation() {
    if (ActivityCompat.checkSelfPermission(this, Manifest.permission.ACCESS_FINE_LOCATION)
        != PackageManager.PERMISSION_GRANTED) {
        Log.w("LocationDebug", "requestFreshLocation: Permission check failed, should not happen.")
        loadWeatherForCity("臺北市")
        return
    }

    Log.d("LocationDebug", "requestFreshLocation: Starting fresh location request with 10s timeout.")

    // 設定 10 秒超時任務
    locationTimeoutRunnable = Runnable {
        Log.w("LocationDebug", "Location request timed out after 50 seconds.")
        stopLocationUpdates() // 停止正在進行的請求
        loadWeatherForCity("臺北市") // 使用預設城市
        isLocationLoaded = true // 標記為已處理，避免重試
    }
    locationTimeoutHandler.postDelayed(locationTimeoutRunnable!!, 50000) // 50秒

    // 建立一個只請求一次的位置請求
    val locationRequest = LocationRequest.create().apply {
        priority = Priority.PRIORITY_HIGH_ACCURACY // 為了確保能拿到，暫時用高精度
        numUpdates = 1 // 只更新一次
    }

    // 定義我們的回呼
    locationCallback = object : LocationCallback() {
        override fun onLocationResult(locationResult: LocationResult) {
            super.onLocationResult(locationResult)
            // 成功取得位置，第一件事就是取消超時任務
            locationTimeoutHandler.removeCallbacks(locationTimeoutRunnable!!)

            val location = locationResult.lastLocation
            if (location != null) {
                Log.d("LocationDebug", "onLocationResult: SUCCESS! Got fresh location.")
                val city = getCityNameFromLocation(location.latitude, location.longitude)
                loadWeatherForCity(city)
            } else {
                Log.w("LocationDebug", "onLocationResult: Fresh location result is null. Using default city.")
                loadWeatherForCity("臺北市")
            }
            isLocationLoaded = true // 無論成功或失敗，都標記為已載入
            // 收到結果後，立刻停止監聽，避免耗電
            stopLocationUpdates()
        }
    }

    // 開始請求位置更新
    Log.d("LocationDebug", "requestFreshLocation: Calling fusedLocationClient.requestLocationUpdates...")
    fusedLocationClient.requestLocationUpdates(locationRequest, locationCallback!!, Looper.getMainLooper())
}

private fun stopLocationUpdates() {
    // 取消可能正在等待的超時任務
    locationTimeoutRunnable?.let {
        locationTimeoutHandler.removeCallbacks(it)
        locationTimeoutRunnable = null
    }
    // 停止位置監聽
    locationCallback?.let {
        fusedLocationClient.removeLocationUpdates(it)
        locationCallback = null
        Log.d("LocationDebug", "stopLocationUpdates: Location updates stopped.")
    }
}

    private fun getCityNameFromLocation(latitude: Double, longitude: Double): String {
        Log.d("LocationDebug", "getCityNameFromLocation: Attempting to geocode ($latitude, $longitude)")
        return try {
            val geocoder = Geocoder(this, Locale.TRADITIONAL_CHINESE)
            val addresses = geocoder.getFromLocation(latitude, longitude, 1)
            if (addresses != null && addresses.isNotEmpty()) {
                val address = addresses[0]
                Log.d("LocationDebug", "getCityNameFromLocation: Geocoder success. Country: ${address.countryName}, City: ${address.locality}, AdminArea: ${address.adminArea}")
                // 檢查國家是否為台灣 (同時相容「臺」和「台」)
                if (address.countryName == "臺灣" || address.countryName == "台灣") {
                    // 🌟 優先使用 adminArea (市/縣)，其次才是 locality (區/里)
                    val cityName = address.adminArea ?: address.locality ?: "臺北市"
                    Log.d("LocationDebug", "getCityNameFromLocation: Located in Taiwan. City: $cityName")
                    // 🌟 直接回傳完整城市名稱，以匹配後端白名單
                    return cityName
                } else {
                    Log.w("LocationDebug", "getCityNameFromLocation: Located outside Taiwan. Using default.")
                    return "臺北市" // 不在台灣，使用預設值
                }
            } else {
                Log.w("LocationDebug", "getCityNameFromLocation: Geocoder returned no addresses. Using default.")
                "臺北市" // 預設值
            }
        } catch (e: Exception) {
            Log.e("LocationDebug", "getCityNameFromLocation: Geocoder failed with exception. Using default.", e)
            "臺北市" // 發生錯誤時的預設值
        }
    }

    override fun onRequestPermissionsResult(
        requestCode: Int,
        permissions: Array<out String>,
        grantResults: IntArray
    ) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == LOCATION_PERMISSION_REQUEST_CODE) {
            if ((grantResults.isNotEmpty() && grantResults[0] == PackageManager.PERMISSION_GRANTED)) {
                // 使用者授予權限
                getLastLocation()
            } else {
                // 使用者拒絕權限，使用預設城市並提示
                Toast.makeText(this, "無法取得位置，將顯示預設天氣資訊", Toast.LENGTH_SHORT).show()
                loadWeatherForCity("臺北市")
            }
        }
    }

    private fun loadWeatherForCity(city: String) {
        val sharedPreferences = getSharedPreferences("user_prefs", Context.MODE_PRIVATE)
        val token = sharedPreferences.getString("token", null)
        val apiService = PlantApiService.create(token)

        apiService.getPlantCareAdvice(city).enqueue(object : Callback<PlantCareAdvice> {
            override fun onResponse(call: Call<PlantCareAdvice>, response: Response<PlantCareAdvice>) {
                if (response.isSuccessful) {
                    val advice = response.body()
                    advice?.let {
                        tvWeatherLocation.text = "地點：${it.location}"
                        tvWeatherInfo.text = "天氣：${it.current_weather.weather} ${it.current_weather.temperature}"
                        tvWateringAdvice.text = "澆水建議：${it.watering_advice}"
                        tvDiseaseAdvice.text = "病害預防：${it.disease_prevention_advice}"
                        tvGeneralCare.text = "一般照護：${it.general_care}"
                    }
                } else {
                    // 處理 API 錯誤，例如顯示預設訊息
                    tvWeatherLocation.text = "地點：$city"
                    tvWeatherInfo.text = "天氣資訊載入失敗"
                    tvWateringAdvice.text = "澆水建議：請確保土壤濕潤"
                    tvDiseaseAdvice.text = "病害預防：請保持通風良好"
                    tvGeneralCare.text = "一般照護：請給予充足陽光"
                }
            }

            override fun onFailure(call: Call<PlantCareAdvice>, t: Throwable) {
                // 處理網路錯誤
                tvWeatherLocation.text = "地點：$city"
                tvWeatherInfo.text = "網路連線失敗"
                tvWateringAdvice.text = "澆水建議：請確保土壤濕潤"
                tvDiseaseAdvice.text = "病害預防：請保持通風良好"
                tvGeneralCare.text = "一般照護：請給予充足陽光"
            }
        })
    }

    private fun showTutorial() {
        val targetColorRes = android.R.color.holo_green_dark
        val sharedPref = getSharedPreferences("PlantDoctor", MODE_PRIVATE)

        val sequence = TapTargetSequence(this)
            .targets(
                TapTarget.forView(cardDiagnose, "植物診斷", "點擊這裡開始辨識您的植物")
                    .outerCircleColor(targetColorRes).targetCircleColor(android.R.color.white).titleTextColor(android.R.color.white).descriptionTextColor(android.R.color.white).cancelable(false).tintTarget(false).transparentTarget(true).drawShadow(true),
                TapTarget.forView(cardWebcam, "即時診斷監控", "開啟相機進行定時自動即時偵測診斷")
                    .outerCircleColor(targetColorRes).targetCircleColor(android.R.color.white).titleTextColor(android.R.color.white).descriptionTextColor(android.R.color.white).cancelable(false).tintTarget(false).transparentTarget(true).drawShadow(true),
                TapTarget.forView(cardHistory, "歷史紀錄", "查看過去的辨識結果")
                    .outerCircleColor(targetColorRes).targetCircleColor(android.R.color.white).titleTextColor(android.R.color.white).descriptionTextColor(android.R.color.white).cancelable(false).tintTarget(false).transparentTarget(true).drawShadow(true),
                TapTarget.forView(cardSettings, "設定", "調整應用程式設定")
                    .outerCircleColor(targetColorRes).targetCircleColor(android.R.color.white).titleTextColor(android.R.color.white).descriptionTextColor(android.R.color.white).cancelable(false).tintTarget(false).transparentTarget(true).drawShadow(true)
            )
            .listener(object : TapTargetSequence.Listener {
                override fun onSequenceFinish() {
                    sharedPref.edit().putBoolean("IS_FIRST_TIME_HOME", false).apply()
                }

                override fun onSequenceStep(lastTarget: TapTarget?, targetClicked: Boolean) {
                    SoundManager.playBubblePop()
                }

                override fun onSequenceCanceled(lastTarget: TapTarget?) {
                    // 如果用戶取消，也標記為已完成，避免下次再跳出
                    sharedPref.edit().putBoolean("IS_FIRST_TIME_HOME", false).apply()
                }
            })
        sequence.start()
    }

    override fun onStop() {
        super.onStop()
        // 在 Activity 不可見時停止位置更新，以節省電力
        stopLocationUpdates()
        SoundManager.stopWind()
        windHandler.removeCallbacks(windRunnable)
    }

    override fun onTouchEvent(event: MotionEvent?): Boolean {
        if (event != null) {
            when (event.action) {
                MotionEvent.ACTION_DOWN -> {
                    windHandler.postDelayed(windRunnable, 500)
                }
                MotionEvent.ACTION_UP, MotionEvent.ACTION_CANCEL -> {
                    windHandler.removeCallbacks(windRunnable)
                    SoundManager.stopWind()
                }
            }
        }
        return super.onTouchEvent(event)
    }

    override fun onDestroy() {
        super.onDestroy()
        windHandler.removeCallbacksAndMessages(null)
    }
}