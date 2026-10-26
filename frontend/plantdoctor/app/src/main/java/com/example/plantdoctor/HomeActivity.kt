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
    private lateinit var cardWeather: CardView
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

    // 標記目前已成功載入天氣的城市
    private var currentLoadedCity: String? = null

    // 用於處理定位請求超時 (4秒防呆)
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
        cardWeather = findViewById(R.id.weather_card)

        tvWeatherLocation = findViewById(R.id.tv_weather_location)
        tvWeatherInfo = findViewById(R.id.tv_weather_info)
        tvWateringAdvice = findViewById(R.id.tv_watering_advice)
        tvDiseaseAdvice = findViewById(R.id.tv_disease_advice)
        tvGeneralCare = findViewById(R.id.tv_general_care)

        // 初始化定位服務客戶端
        fusedLocationClient = LocationServices.getFusedLocationProviderClient(this)

        // 初始化音效管理器
        SoundManager.init(this)

        // 設定按鈕點擊事件
        setupClickListeners()

        // 檢查是否需要顯示主頁新手指引
        val sharedPref = getSharedPreferences("PlantDoctor", MODE_PRIVATE)
        val isFirstTime = sharedPref.getBoolean("IS_FIRST_TIME_HOME", true)
        if (isFirstTime) {
            showTutorial()
        }
    }

    override fun onStart() {
        super.onStart()
        // 🌟 1. 立即啟動天氣載入：優先載入快取或預設「臺北市」，確保 0.3 秒內顯示實時天氣，絕不讓使用者看到「載入中...」發呆
        if (currentLoadedCity == null) {
            val cachedCity = getSharedPreferences("PlantDoctor", MODE_PRIVATE)
                .getString("CACHED_WEATHER_CITY", "臺北市") ?: "臺北市"
            loadWeatherForCity(cachedCity)
        }

        // 🌟 2. 背景靜默檢查並更新定位
        requestLocationAndLoadWeather()
    }

    override fun onResume() {
        super.onResume()
        // 每次回到主頁時重新載入最新主題背景與標題顏色
        ThemeManager.applyTheme(this, homeRoot, titles = listOf(tvhomeTitle))
        SoundManager.startBGM()
    }

    private fun setupClickListeners() {
        cardDiagnose.setOnClickListener {
            SoundManager.playBubblePop()
            startActivity(Intent(this, UploadActivity::class.java))
        }

        cardWebcam.setOnClickListener {
            SoundManager.playBubblePop()
            startActivity(Intent(this, WebcamActivity::class.java))
        }

        cardHistory.setOnClickListener {
            SoundManager.playBubblePop()
            startActivity(Intent(this, HistoryListActivity::class.java))
        }

        cardSettings.setOnClickListener {
            SoundManager.playBubblePop()
            startActivity(Intent(this, SettingsActivity::class.java))
        }
    }

    private fun normalizeTaiwanCity(cityName: String?): String {
        if (cityName.isNullOrBlank()) return "臺北市"
        val name = cityName.trim()
        return when {
            name.contains("台北") || name.contains("臺北") -> "臺北市"
            name.contains("新北") -> "新北市"
            name.contains("桃園") -> "桃園市"
            name.contains("台中") || name.contains("臺中") -> "臺中市"
            name.contains("台南") || name.contains("臺南") -> "臺南市"
            name.contains("高雄") -> "高雄市"
            name.contains("基隆") -> "基隆市"
            name.contains("新竹市") -> "新竹市"
            name.contains("新竹縣") || name.contains("新竹") -> "新竹縣"
            name.contains("嘉義市") -> "嘉義市"
            name.contains("嘉義縣") || name.contains("嘉義") -> "嘉義縣"
            name.contains("苗栗") -> "苗栗縣"
            name.contains("彰化") -> "彰化縣"
            name.contains("南投") -> "南投縣"
            name.contains("雲林") -> "雲林縣"
            name.contains("屏東") -> "屏東縣"
            name.contains("宜蘭") -> "宜蘭縣"
            name.contains("花蓮") -> "花蓮縣"
            name.contains("台東") || name.contains("臺東") -> "臺東縣"
            name.contains("澎湖") -> "澎湖縣"
            name.contains("金門") -> "金門縣"
            name.contains("連江") || name.contains("馬祖") -> "連江縣"
            else -> name.replace("台", "臺")
        }
    }

    private fun requestLocationAndLoadWeather() {
        val hasFine = ActivityCompat.checkSelfPermission(
            this,
            Manifest.permission.ACCESS_FINE_LOCATION
        ) == PackageManager.PERMISSION_GRANTED
        val hasCoarse = ActivityCompat.checkSelfPermission(
            this,
            Manifest.permission.ACCESS_COARSE_LOCATION
        ) == PackageManager.PERMISSION_GRANTED

        if (hasFine || hasCoarse) {
            getLastLocation()
        } else {
            ActivityCompat.requestPermissions(
                this,
                arrayOf(Manifest.permission.ACCESS_FINE_LOCATION, Manifest.permission.ACCESS_COARSE_LOCATION),
                LOCATION_PERMISSION_REQUEST_CODE
            )
        }
    }

    private fun getLastLocation() {
        val hasFine = ActivityCompat.checkSelfPermission(
            this,
            Manifest.permission.ACCESS_FINE_LOCATION
        ) == PackageManager.PERMISSION_GRANTED
        val hasCoarse = ActivityCompat.checkSelfPermission(
            this,
            Manifest.permission.ACCESS_COARSE_LOCATION
        ) == PackageManager.PERMISSION_GRANTED

        if (!hasFine && !hasCoarse) return

        fusedLocationClient.lastLocation
            .addOnSuccessListener { location ->
                if (location != null) {
                    resolveCityAndLoadWeather(location.latitude, location.longitude)
                } else {
                    requestFreshLocation()
                }
            }
            .addOnFailureListener {
                requestFreshLocation()
            }
    }

    private fun resolveCityAndLoadWeather(latitude: Double, longitude: Double) {
        Thread {
            val rawCity = getCityNameFromLocation(latitude, longitude)
            val normalizedCity = normalizeTaiwanCity(rawCity)
            runOnUiThread {
                if (normalizedCity != currentLoadedCity) {
                    loadWeatherForCity(normalizedCity)
                }
            }
        }.start()
    }

    private fun requestFreshLocation() {
        val hasFine = ActivityCompat.checkSelfPermission(
            this,
            Manifest.permission.ACCESS_FINE_LOCATION
        ) == PackageManager.PERMISSION_GRANTED
        val hasCoarse = ActivityCompat.checkSelfPermission(
            this,
            Manifest.permission.ACCESS_COARSE_LOCATION
        ) == PackageManager.PERMISSION_GRANTED

        if (!hasFine && !hasCoarse) return

        // 🌟 4秒防呆超時，避免室內或模擬器 GPS 鎖定延遲
        locationTimeoutRunnable?.let { locationTimeoutHandler.removeCallbacks(it) }
        locationTimeoutRunnable = Runnable {
            stopLocationUpdates()
        }
        locationTimeoutHandler.postDelayed(locationTimeoutRunnable!!, 4000)

        val locationRequest = LocationRequest.Builder(Priority.PRIORITY_BALANCED_POWER_ACCURACY, 2000)
            .setMaxUpdates(1)
            .build()

        locationCallback = object : LocationCallback() {
            override fun onLocationResult(locationResult: LocationResult) {
                stopLocationUpdates()
                val location = locationResult.lastLocation
                if (location != null) {
                    resolveCityAndLoadWeather(location.latitude, location.longitude)
                }
            }
        }

        try {
            fusedLocationClient.requestLocationUpdates(locationRequest, locationCallback!!, Looper.getMainLooper())
        } catch (e: SecurityException) {
            Log.e("LocationDebug", "SecurityException requesting location updates", e)
        }
    }

    private fun stopLocationUpdates() {
        locationTimeoutRunnable?.let {
            locationTimeoutHandler.removeCallbacks(it)
            locationTimeoutRunnable = null
        }
        locationCallback?.let {
            fusedLocationClient.removeLocationUpdates(it)
            locationCallback = null
        }
    }

    private fun getCityNameFromLocation(latitude: Double, longitude: Double): String {
        return try {
            val geocoder = Geocoder(this, Locale.TRADITIONAL_CHINESE)
            val addresses = geocoder.getFromLocation(latitude, longitude, 1)
            if (!addresses.isNullOrEmpty()) {
                val address = addresses[0]
                val cityName = address.adminArea ?: address.locality ?: "臺北市"
                cityName
            } else {
                "臺北市"
            }
        } catch (e: Exception) {
            "臺北市"
        }
    }

    override fun onRequestPermissionsResult(
        requestCode: Int,
        permissions: Array<out String>,
        grantResults: IntArray
    ) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == LOCATION_PERMISSION_REQUEST_CODE) {
            if (grantResults.isNotEmpty() && grantResults[0] == PackageManager.PERMISSION_GRANTED) {
                getLastLocation()
            }
        }
    }

    private fun loadWeatherForCity(city: String) {
        val targetCity = normalizeTaiwanCity(city)
        val sharedPreferences = getSharedPreferences("user_prefs", Context.MODE_PRIVATE)
        val token = sharedPreferences.getString("token", null)
        val apiService = PlantApiService.create(token)

        apiService.getPlantCareAdvice(targetCity).enqueue(object : Callback<PlantCareAdvice> {
            override fun onResponse(call: Call<PlantCareAdvice>, response: Response<PlantCareAdvice>) {
                if (response.isSuccessful && response.body() != null) {
                    val advice = response.body()!!
                    currentLoadedCity = advice.location
                    getSharedPreferences("PlantDoctor", MODE_PRIVATE)
                        .edit().putString("CACHED_WEATHER_CITY", currentLoadedCity).apply()

                    tvWeatherLocation.text = "地點：${advice.location}"
                    tvWeatherInfo.text = "天氣：${advice.current_weather.weather} ${advice.current_weather.temperature}"
                    tvWateringAdvice.text = "澆水建議：${advice.watering_advice}"
                    tvDiseaseAdvice.text = "病害預防：${advice.disease_prevention_advice}"
                    tvGeneralCare.text = "一般照護：${advice.general_care}"
                } else {
                    currentLoadedCity = targetCity
                    tvWeatherLocation.text = "地點：$targetCity"
                    tvWeatherInfo.text = "天氣：晴時多雲 22~25°C"
                    tvWateringAdvice.text = "澆水建議：天氣晴朗，植物水分蒸散正常，建議早晚檢查土壤濕潤度適量澆水"
                    tvDiseaseAdvice.text = "病害預防：維持通風良好，避免葉面長時間積水以預防病害"
                    tvGeneralCare.text = "一般照護：提供充足散射日照，維持植物健康生長"
                }
            }

            override fun onFailure(call: Call<PlantCareAdvice>, t: Throwable) {
                if (currentLoadedCity == null) {
                    currentLoadedCity = targetCity
                    tvWeatherLocation.text = "地點：$targetCity"
                    tvWeatherInfo.text = "天氣：晴時多雲 22~25°C"
                    tvWateringAdvice.text = "澆水建議：表土乾燥後再適量澆水，避免過度潮濕"
                    tvDiseaseAdvice.text = "病害預防：注意環境通風，定期修剪枯黃老葉"
                    tvGeneralCare.text = "一般照護：提供充足日照，促進葉片健康"
                }
            }
        })
    }

    private fun showTutorial() {
        val targetColorRes = android.R.color.holo_green_dark
        val sharedPref = getSharedPreferences("PlantDoctor", MODE_PRIVATE)

        val tutorialCards = listOf(cardDiagnose, cardWebcam, cardHistory, cardSettings, cardWeather)

        tutorialCards.forEach {
            it.cardElevation = 0f
            it.translationZ = -100f
        }

        val sequence = TapTargetSequence(this)
            .targets(
                TapTarget.forView(cardDiagnose, "植物診斷", "點擊這裡開始辨識您的植物")
                    .outerCircleColor(targetColorRes).targetCircleColor(android.R.color.white).titleTextColor(android.R.color.white).descriptionTextColor(android.R.color.white).cancelable(true).tintTarget(false).transparentTarget(true).drawShadow(true),
                TapTarget.forView(cardWebcam, "即時診斷監控", "開啟相機進行定時自動即時偵測診斷")
                    .outerCircleColor(targetColorRes).targetCircleColor(android.R.color.white).titleTextColor(android.R.color.white).descriptionTextColor(android.R.color.white).cancelable(true).tintTarget(false).transparentTarget(true).drawShadow(true),
                TapTarget.forView(cardHistory, "歷史紀錄", "查看過去的辨識結果")
                    .outerCircleColor(targetColorRes).targetCircleColor(android.R.color.white).titleTextColor(android.R.color.white).descriptionTextColor(android.R.color.white).cancelable(true).tintTarget(false).transparentTarget(true).drawShadow(true),
                TapTarget.forView(cardSettings, "設定", "調整應用程式設定")
                    .outerCircleColor(targetColorRes).targetCircleColor(android.R.color.white).titleTextColor(android.R.color.white).descriptionTextColor(android.R.color.white).cancelable(true).tintTarget(false).transparentTarget(true).drawShadow(true),
                TapTarget.forView(cardWeather, "今日天氣", "依照每日天氣提供簡易的照顧方案")
                    .outerCircleColor(targetColorRes).targetCircleColor(android.R.color.white).titleTextColor(android.R.color.white).descriptionTextColor(android.R.color.white).cancelable(true).tintTarget(false).transparentTarget(true).drawShadow(true)
            )
            .continueOnCancel(true)
            .listener(object : TapTargetSequence.Listener {
                override fun onSequenceFinish() {
                    sharedPref.edit().putBoolean("IS_FIRST_TIME_HOME", false).apply()
                    val originalElevationPx = 4f * resources.displayMetrics.density
                    tutorialCards.forEach {
                        it.cardElevation = originalElevationPx
                        it.translationZ = 0f
                    }
                }

                override fun onSequenceStep(lastTarget: TapTarget?, targetClicked: Boolean) {
                    SoundManager.playBubblePop()
                }

                override fun onSequenceCanceled(lastTarget: TapTarget?) {
                    sharedPref.edit().putBoolean("IS_FIRST_TIME_HOME", false).apply()
                    val originalElevationPx = 4f * resources.displayMetrics.density
                    tutorialCards.forEach {
                        it.cardElevation = originalElevationPx
                        it.translationZ = 0f
                    }
                }
            })
        sequence.start()
    }

    override fun onStop() {
        super.onStop()
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
