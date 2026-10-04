package com.example.plantdoctor

import android.Manifest
import android.app.Activity
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.net.Uri
import android.os.Bundle
import android.os.Environment
import android.os.Handler
import android.os.Looper
import android.provider.MediaStore
import android.util.Log
import android.view.MotionEvent
import android.widget.Button
import android.widget.ImageButton
import android.widget.ImageView
import android.widget.TextView
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.constraintlayout.widget.ConstraintLayout
import androidx.core.content.ContextCompat
import androidx.core.content.FileProvider
import com.bumptech.glide.Glide
import java.io.File
import java.io.FileOutputStream
import java.io.InputStream
import java.text.SimpleDateFormat
import java.util.*

import android.content.res.ColorStateList
import android.graphics.Color
import android.graphics.drawable.GradientDrawable
import android.text.Editable
import android.text.TextWatcher
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.ListView
import retrofit2.Call
import retrofit2.Callback
import retrofit2.Response

class UploadActivity : AppCompatActivity() {

    private var selectedImageUri: Uri? = null
    private lateinit var imgPreview: ImageView
    private var photoFile: File? = null

    private lateinit var uploadRoot: ConstraintLayout

    // 🌟 作物下拉選單相關
    private var selectedCropName: String = "未知"
    private val defaultCommonCrops = listOf(
        "未知", "檸檬", "草莓", "番茄", "水稻", "玉米", "胡瓜", "柑橘", "葡萄",
        "蓮霧", "芒果", "木瓜", "西瓜", "茄子", "甜椒", "茶", "香蕉", "馬鈴薯",
        "甘藍", "青花菜", "洋蔥", "蘋果", "梨", "桃"
    )
    private val cropList: MutableList<String> = defaultCommonCrops.toMutableList()
    private var cropDialog: androidx.appcompat.app.AlertDialog? = null
    private var cropAdapter: android.widget.ArrayAdapter<String>? = null
    private var cropDisplayList: ArrayList<String>? = null
    private lateinit var layoutCropSelector: LinearLayout
    private lateinit var tvCropLabel: TextView
    private lateinit var tvSelectedCrop: TextView
    private lateinit var ivCropDropdownArrow: ImageView

    // 🌟 1. 建立風聲延遲計時器與任務
    private val windHandler = Handler(Looper.getMainLooper())
    private val windRunnable = Runnable {
        SoundManager.startWind()
    }

    // --- 1. 相機權限請求處理 ---
    private val requestCameraPermissionLauncher = registerForActivityResult(ActivityResultContracts.RequestPermission()) { isGranted ->
        if (isGranted) {
            openCamera()
        } else {
            Toast.makeText(this, "需要相機權限才能拍照喔！", Toast.LENGTH_SHORT).show()
        }
    }

    // --- 2. 相簿選擇處理 ---
    private val selectImageLauncher = registerForActivityResult(ActivityResultContracts.StartActivityForResult()) { result ->
        Log.d("UPLOAD_DEBUG", "selectImageLauncher callback triggered. Result code: ${result.resultCode}")
        if (result.resultCode == Activity.RESULT_OK) {
            val uri = result.data?.data
            if (uri != null) {
                try {
                    contentResolver.takePersistableUriPermission(uri, Intent.FLAG_GRANT_READ_URI_PERMISSION)
                } catch (e: Exception) { e.printStackTrace() }
                updateImagePreview(uri)
            }
        }
    }

    // --- 3. 相機拍照處理 ---
    private val takePhotoLauncher = registerForActivityResult(ActivityResultContracts.StartActivityForResult()) { result ->
        if (result.resultCode == Activity.RESULT_OK) {
            selectedImageUri?.let { updateImagePreview(it) }
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_upload)

        // --- 2. 綁定 UI 元件 ---
        uploadRoot = findViewById(R.id.upload_root_layout)
        imgPreview = findViewById(R.id.img_preview)
        val btnBack = findViewById<ImageButton>(R.id.btn_back_home)
        val btnCamera = findViewById<Button>(R.id.btn_camera)
        val btnAlbum = findViewById<Button>(R.id.btn_album)
        val btnAnalyze = findViewById<Button>(R.id.btn_analyze)
        val tvUploadTitle = findViewById<TextView>(R.id.tv_upload_title)

        // 作物下拉選單元件綁定
        layoutCropSelector = findViewById(R.id.layout_crop_selector)
        tvCropLabel = findViewById(R.id.tv_crop_label)
        tvSelectedCrop = findViewById(R.id.tv_selected_crop)
        ivCropDropdownArrow = findViewById(R.id.iv_crop_dropdown_arrow)

        // 🌟 初始化音效管理器 (與 LoginActivity 對齊)
        SoundManager.init(this)

        // 召喚大總管聯動主題
        ThemeManager.applyTheme(
            context = this,
            rootLayout = uploadRoot,
            mainButtons = listOf(btnCamera, btnAlbum, btnAnalyze),
            titles = listOf(tvUploadTitle),
            imageButtons = listOf(btnBack)
        )
        applyCropTheme()

        layoutCropSelector.setOnClickListener {
            SoundManager.playBubblePop()
            showCropSelectionDialog()
        }

        loadCachedCrops()
        fetchCropsList()

        imgPreview.setOnClickListener {
            SoundManager.playBubblePop()
            openAlbum()
        }

        btnAlbum.setOnClickListener {
            SoundManager.playBubblePop()
            openAlbum()
        }

        btnBack.setOnClickListener {
            SoundManager.playBubblePop()
            finish()
        }

        btnCamera.setOnClickListener {
            SoundManager.playBubblePop()
            checkCameraPermission()
        }

        btnAnalyze.setOnClickListener {
            SoundManager.playBubblePop()

            if (selectedImageUri != null) {
                val sharedPref = getSharedPreferences("PlantDoctor", Context.MODE_PRIVATE)
                val token = sharedPref.getString("token", null)

                if (token.isNullOrEmpty()) {
                    val intent = Intent(this, LoginActivity::class.java)
                    intent.flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
                    startActivity(intent)
                    return@setOnClickListener
                }

                cropDialog?.dismiss()
                val intent = Intent(this, DiagnoseProgressActivity::class.java)
                intent.putExtra("IMAGE_URI", selectedImageUri.toString())
                intent.putExtra("CROP_NAME", selectedCropName)
                intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
                startActivity(intent)
                finish()
            } else {
                Toast.makeText(this, "請先選擇一張照片", Toast.LENGTH_SHORT).show()
            }
        }
    }

    override fun onResume() {
        super.onResume()
        // 🌟 每次回到頁面時，重新刷新主題色彩與啟動背景音樂 (對齊 LoginActivity 邏輯)
        if (::uploadRoot.isInitialized) {
            val btnBack = findViewById<ImageButton>(R.id.btn_back_home)
            val btnCamera = findViewById<Button>(R.id.btn_camera)
            val btnAlbum = findViewById<Button>(R.id.btn_album)
            val btnAnalyze = findViewById<Button>(R.id.btn_analyze)
            val tvUploadTitle = findViewById<TextView>(R.id.tv_upload_title)

            ThemeManager.applyTheme(
                context = this,
                rootLayout = uploadRoot,
                mainButtons = listOf(btnCamera, btnAlbum, btnAnalyze),
                titles = listOf(tvUploadTitle),
                imageButtons = listOf(btnBack)
            )
            applyCropTheme()
        }
        SoundManager.startBGM()
    }

    private fun getThemeMainColor(): Int {
        val sharedPref = getSharedPreferences("PlantDoctor", Context.MODE_PRIVATE)
        val themeId = sharedPref.getInt("THEME_COLOR_ID", 0)
        val colorStr = when (themeId) {
            1 -> "#1565C0"
            2 -> "#D84315"
            3 -> "#AD1457"
            else -> "#2E7D32"
        }
        return Color.parseColor(colorStr)
    }

    private fun applyCropTheme() {
        val mainColor = getThemeMainColor()
        if (::tvCropLabel.isInitialized) {
            tvCropLabel.setTextColor(mainColor)
        }
        if (::ivCropDropdownArrow.isInitialized) {
            ivCropDropdownArrow.imageTintList = ColorStateList.valueOf(mainColor)
        }
        if (::layoutCropSelector.isInitialized) {
            val selectorBg = GradientDrawable().apply {
                setColor(Color.WHITE)
                cornerRadius = 16f * resources.displayMetrics.density
                setStroke((2 * resources.displayMetrics.density).toInt(), mainColor)
            }
            layoutCropSelector.background = selectorBg
        }
    }

    private fun loadCachedCrops() {
        val sharedPref = getSharedPreferences("PlantDoctor", Context.MODE_PRIVATE)
        val cached = sharedPref.getStringSet("CACHED_CROPS", null)
        if (!cached.isNullOrEmpty()) {
            cropList.clear()
            cropList.add("未知")
            val sortedList = cached.filter { it != "未知" }.sorted()
            cropList.addAll(sortedList)
        }
    }

    private fun fetchCropsList() {
        val sharedPref = getSharedPreferences("PlantDoctor", Context.MODE_PRIVATE)
        val token = sharedPref.getString("token", null)
        val apiService = PlantApiService.create(token)

        apiService.getCrops().enqueue(object : Callback<CropsResponse> {
            override fun onResponse(call: Call<CropsResponse>, response: Response<CropsResponse>) {
                if (response.isSuccessful) {
                    val rawCrops = response.body()?.data
                    if (!rawCrops.isNullOrEmpty()) {
                        cropList.clear()
                        val filtered = rawCrops.toMutableList()
                        if (filtered.remove("未知")) {
                            cropList.add("未知")
                        } else {
                            cropList.add("未知")
                        }
                        cropList.addAll(filtered)
                        sharedPref.edit().putStringSet("CACHED_CROPS", cropList.toSet()).apply()
                        Log.d("UPLOAD_CROP", "成功自後端載入 ${cropList.size} 種作物！")

                        runOnUiThread {
                            cropDisplayList?.let { list ->
                                list.clear()
                                list.addAll(cropList)
                                cropAdapter?.notifyDataSetChanged()
                            }
                        }
                    }
                }
            }

            override fun onFailure(call: Call<CropsResponse>, t: Throwable) {
                Log.w("UPLOAD_CROP", "載入作物清單失敗，將使用預設設定: ${t.message}")
            }
        })
    }

    private fun showCropSelectionDialog() {
        cropDialog?.dismiss()
        val dialogView = layoutInflater.inflate(R.layout.dialog_select_crop, null)
        val dialog = androidx.appcompat.app.AlertDialog.Builder(this)
            .setView(dialogView)
            .create()
        cropDialog = dialog

        dialog.window?.setBackgroundDrawableResource(android.R.color.transparent)

        val tvDialogTitle = dialogView.findViewById<TextView>(R.id.tv_dialog_title)
        val btnClose = dialogView.findViewById<ImageButton>(R.id.btn_dialog_close)
        val etSearch = dialogView.findViewById<EditText>(R.id.et_crop_search)
        val btnClear = dialogView.findViewById<ImageButton>(R.id.btn_clear_search)
        val lvCrops = dialogView.findViewById<ListView>(R.id.lv_crops)

        val themeColor = getThemeMainColor()
        tvDialogTitle.setTextColor(themeColor)

        val displayList = ArrayList(cropList)
        cropDisplayList = displayList
        val adapter = object : android.widget.ArrayAdapter<String>(this, R.layout.item_crop_dialog, R.id.tv_crop_item_name, displayList) {
            override fun getView(position: Int, convertView: android.view.View?, parent: android.view.ViewGroup): android.view.View {
                val view = super.getView(position, convertView, parent)
                val item = getItem(position) ?: ""
                val tvName = view.findViewById<TextView>(R.id.tv_crop_item_name)
                val tvTag = view.findViewById<TextView>(R.id.tv_crop_item_tag)

                tvName.text = item
                if (item == "未知") {
                    tvTag.visibility = android.view.View.VISIBLE
                    tvTag.text = "預設 (AI自動識別)"
                    tvTag.setTextColor(themeColor)
                } else {
                    tvTag.visibility = android.view.View.GONE
                }

                if (item == selectedCropName) {
                    tvName.setTextColor(themeColor)
                    tvName.typeface = android.graphics.Typeface.DEFAULT_BOLD
                } else {
                    tvName.setTextColor(Color.parseColor("#333333"))
                    tvName.typeface = android.graphics.Typeface.DEFAULT
                }

                view.setOnClickListener {
                    selectedCropName = item
                    tvSelectedCrop.text = item
                    SoundManager.playBubblePop()
                    dialog.dismiss()
                }

                return view
            }
        }
        cropAdapter = adapter
        lvCrops.adapter = adapter

        lvCrops.setOnItemClickListener { _, _, position, _ ->
            val chosen = adapter.getItem(position) ?: "未知"
            selectedCropName = chosen
            tvSelectedCrop.text = chosen
            SoundManager.playBubblePop()
            dialog.dismiss()
        }

        etSearch.addTextChangedListener(object : TextWatcher {
            override fun beforeTextChanged(s: CharSequence?, start: Int, count: Int, after: Int) {}
            override fun onTextChanged(s: CharSequence?, start: Int, before: Int, count: Int) {
                val query = s?.toString()?.trim() ?: ""
                btnClear.visibility = if (query.isNotEmpty()) android.view.View.VISIBLE else android.view.View.GONE

                displayList.clear()
                if (query.isEmpty()) {
                    displayList.addAll(cropList)
                } else {
                    for (crop in cropList) {
                        if (crop.contains(query, ignoreCase = true)) {
                            displayList.add(crop)
                        }
                    }
                }
                adapter.notifyDataSetChanged()
            }
            override fun afterTextChanged(s: Editable?) {}
        })

        btnClear.setOnClickListener {
            etSearch.setText("")
        }

        btnClose.setOnClickListener {
            SoundManager.playBubblePop()
            dialog.dismiss()
        }

        dialog.setOnDismissListener {
            if (cropDialog === dialog) {
                cropDialog = null
                cropAdapter = null
                cropDisplayList = null
            }
        }

        dialog.show()
    }

    /**
     * 🌟 核心關鍵突破：搶在 ScrollView 吃掉事件之前分發 Touch 事件！
     * 無論頁面是否有 NestedScrollView 滾動，按住畫面 0.5 秒依然會吹起風聲。
     */
    override fun dispatchTouchEvent(ev: MotionEvent?): Boolean {
        if (ev != null) {
            when (ev.action) {
                MotionEvent.ACTION_DOWN -> {
                    windHandler.postDelayed(windRunnable, 500)
                }
                MotionEvent.ACTION_UP, MotionEvent.ACTION_CANCEL -> {
                    windHandler.removeCallbacks(windRunnable)
                    SoundManager.stopWind()
                }
            }
        }
        return super.dispatchTouchEvent(ev)
    }

    private fun getCachePathFromUri(context: Context, uri: Uri): String {
        return try {
            val inputStream = context.contentResolver.openInputStream(uri)
            val tempFile = File(context.cacheDir, "temp_mock_plant_image.jpg")
            val outputStream = FileOutputStream(tempFile)

            inputStream?.use { input ->
                outputStream.use { output ->
                    input.copyTo(output)
                }
            }
            tempFile.absolutePath
        } catch (e: Exception) {
            e.printStackTrace()
            uri.toString()
        }
    }

    private fun checkCameraPermission() {
        when {
            ContextCompat.checkSelfPermission(this, Manifest.permission.CAMERA) == PackageManager.PERMISSION_GRANTED -> {
                openCamera()
            }
            else -> {
                requestCameraPermissionLauncher.launch(Manifest.permission.CAMERA)
            }
        }
    }

    private fun openAlbum() {
        val intent = Intent(Intent.ACTION_OPEN_DOCUMENT).apply {
            addCategory(Intent.CATEGORY_OPENABLE)
            type = "image/*"
        }
        selectImageLauncher.launch(intent)
    }

    private fun openCamera() {
        try {
            val intent = Intent(MediaStore.ACTION_IMAGE_CAPTURE)
            photoFile = createImageFile()

            photoFile?.let {
                val authority = "com.example.plantdoctor.fileprovider"
                val photoURI: Uri = FileProvider.getUriForFile(this, authority, it)
                selectedImageUri = photoURI
                intent.putExtra(MediaStore.EXTRA_OUTPUT, photoURI)
                intent.addFlags(Intent.FLAG_GRANT_WRITE_URI_PERMISSION)
                takePhotoLauncher.launch(intent)
            }
        } catch (e: Exception) {
            e.printStackTrace()
            Toast.makeText(this, "失敗: ${e.message}", Toast.LENGTH_SHORT).show()
        }
    }

    private fun createImageFile(): File? {
        val timeStamp: String = SimpleDateFormat("yyyyMMdd_HHmmss", Locale.getDefault()).format(Date())
        val storageDir: File? = getExternalFilesDir(Environment.DIRECTORY_PICTURES)
        return File.createTempFile("JPEG_${timeStamp}_", ".jpg", storageDir)
    }

    private fun updateImagePreview(uri: Uri) {
        Thread {
            val compressedFile = compressImage(this, uri)
            if (compressedFile != null) {
                val compressedUri = Uri.fromFile(compressedFile)

                runOnUiThread {
                    selectedImageUri = compressedUri

                    Glide.with(this)
                        .load(compressedUri)
                        .centerCrop()
                        .into(imgPreview)
                }
            } else {
                runOnUiThread {
                    selectedImageUri = uri

                    Glide.with(this)
                        .load(uri)
                        .centerCrop()
                        .into(imgPreview)
                }
            }
        }.start()
    }

    private fun compressImage(context: Context, imageUri: Uri): File? {
        var inputStream: InputStream? = null
        try {
            val options = BitmapFactory.Options().apply { inJustDecodeBounds = true }
            inputStream = context.contentResolver.openInputStream(imageUri)
            BitmapFactory.decodeStream(inputStream, null, options)
            inputStream?.close()

            val originalWidth = options.outWidth
            val originalHeight = options.outHeight
            if (originalWidth <= 0 || originalHeight <= 0) return null

            val maxSide = 1080
            var sampleSize = 1
            if (originalWidth > maxSide || originalHeight > maxSide) {
                val halfWidth = originalWidth / 2
                val halfHeight = originalHeight / 2
                while ((halfWidth / sampleSize) >= maxSide || (halfHeight / sampleSize) >= maxSide) {
                    sampleSize *= 2
                }
            }

            val decodeOptions = BitmapFactory.Options().apply { inSampleSize = sampleSize }
            inputStream = context.contentResolver.openInputStream(imageUri)
            val scaledBitmap = BitmapFactory.decodeStream(inputStream, null, decodeOptions)
            inputStream?.close()

            if (scaledBitmap == null) return null

            val timeStamp = SimpleDateFormat("yyyyMMdd_HHmmss", Locale.getDefault()).format(Date())
            val cacheFile = File(context.cacheDir, "mini_${timeStamp}.jpg")

            val fileOutputStream = FileOutputStream(cacheFile)
            scaledBitmap.compress(Bitmap.CompressFormat.JPEG, 80, fileOutputStream)
            fileOutputStream.flush()
            fileOutputStream.close()

            scaledBitmap.recycle()

            Log.d("IMAGE_COMPRESS", "壓縮成功！新檔案大小：${cacheFile.length() / 1024} KB")
            return cacheFile

        } catch (e: Exception) {
            e.printStackTrace()
            return null
        } finally {
            inputStream?.close()
        }
    }

    override fun onStop() {
        super.onStop()
        cropDialog?.dismiss()
        SoundManager.stopWind()
        windHandler.removeCallbacks(windRunnable)
    }

    override fun onDestroy() {
        super.onDestroy()
        cropDialog?.dismiss()
        windHandler.removeCallbacksAndMessages(null)
    }
}