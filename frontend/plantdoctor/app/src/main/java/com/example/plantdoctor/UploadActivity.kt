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
import android.view.MotionEvent
import android.provider.MediaStore
import android.util.Log
import android.widget.Button
import android.widget.ImageButton
import android.widget.ImageView
import android.widget.Toast
import android.widget.TextView
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

class UploadActivity : AppCompatActivity() {

    private var selectedImageUri: Uri? = null
    private lateinit var imgPreview: ImageView
    private var photoFile: File? = null

    // 🌟 建立風聲延遲計時器與任務
    private val windHandler = Handler(Looper.getMainLooper())
    private val windRunnable = Runnable {
        SoundManager.startWind()
    }

    // --- 1. 相權限請求處理 ---
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
        val uploadRoot = findViewById<ConstraintLayout>(R.id.upload_root_layout)
        imgPreview = findViewById(R.id.img_preview)
        val btnBack = findViewById<ImageButton>(R.id.btn_back_home)
        val btnCamera = findViewById<Button>(R.id.btn_camera)
        val btnAlbum = findViewById<Button>(R.id.btn_album)
        val btnAnalyze = findViewById<Button>(R.id.btn_analyze)
        val tvUploadTitle = findViewById<TextView>(R.id.tv_upload_title)

        // 召喚大總管聯動主題
        ThemeManager.applyTheme(
            context = this,
            rootLayout = uploadRoot,
            mainButtons = listOf(btnCamera, btnAlbum, btnAnalyze),
            titles = listOf(tvUploadTitle),
            imageButtons = listOf(btnBack)
        )

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

                // 這裡傳出去的 selectedImageUri 已經是縮小過後的精華小檔案囉！
                val intent = Intent(this, DiagnoseProgressActivity::class.java)
                intent.putExtra("IMAGE_URI", selectedImageUri.toString())
                intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
                startActivity(intent)
            } else {
                Toast.makeText(this, "請先選擇一張照片", Toast.LENGTH_SHORT).show()
            }
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

    // 🌟 核心增強：在預覽與指派 Uri 前，先在背景進行高效壓縮
    private fun updateImagePreview(uri: Uri) {
        // 為了避免大圖卡住 UI 執行緒，使用執行緒進行非同步壓縮
        Thread {
            val compressedFile = compressImage(this, uri)
            if (compressedFile != null) {
                val compressedUri = Uri.fromFile(compressedFile)

                // 壓縮成功，切回主執行緒更新 UI 與暫存變數
                runOnUiThread {
                    selectedImageUri = compressedUri

                    // 🌟 核心對接：把剛剛壓縮完成的快取 Uri 字串偷偷塞給假 API 的暫存器！
                    // PlantApiService.latestMockImageUri = compressedUri.toString()

                    Glide.with(this)
                        .load(compressedUri)
                        .centerCrop()
                        .into(imgPreview)
                }
            } else {
                // 如果壓縮有萬一失敗，則備用原本的 Uri 確保程式不崩潰
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

    // 🌟 核心新增：等比例縮放 + JPEG 80% 壓縮演算法
    private fun compressImage(context: Context, imageUri: Uri): File? {
        var inputStream: InputStream? = null
        try {
            // 1. 先讀取圖片尺寸（不載入整張圖，避免 OOM 記憶體溢出）
            val options = BitmapFactory.Options().apply { inJustDecodeBounds = true }
            inputStream = context.contentResolver.openInputStream(imageUri)
            BitmapFactory.decodeStream(inputStream, null, options)
            inputStream?.close()

            val originalWidth = options.outWidth
            val originalHeight = options.outHeight
            if (originalWidth <= 0 || originalHeight <= 0) return null

            // 2. 計算等比例縮小的比例（設定上限最大邊 1080 像素）
            val maxSide = 1080
            var sampleSize = 1
            if (originalWidth > maxSide || originalHeight > maxSide) {
                val halfWidth = originalWidth / 2
                val halfHeight = originalHeight / 2
                while ((halfWidth / sampleSize) >= maxSide || (halfHeight / sampleSize) >= maxSide) {
                    sampleSize *= 2
                }
            }

            // 3. 真正解碼載入縮小後的縮圖
            val decodeOptions = BitmapFactory.Options().apply { inSampleSize = sampleSize }
            inputStream = context.contentResolver.openInputStream(imageUri)
            val scaledBitmap = BitmapFactory.decodeStream(inputStream, null, decodeOptions)
            inputStream?.close()

            if (scaledBitmap == null) return null

            // 4. 創造一個專屬的內部壓縮快取檔
            val timeStamp = SimpleDateFormat("yyyyMMdd_HHmmss", Locale.getDefault()).format(Date())
            val cacheFile = File(context.cacheDir, "mini_${timeStamp}.jpg")

            // 5. 壓進去！設定 JPEG 與 80% 高清品質
            val fileOutputStream = FileOutputStream(cacheFile)
            scaledBitmap.compress(Bitmap.CompressFormat.JPEG, 80, fileOutputStream)
            fileOutputStream.flush()
            fileOutputStream.close()

            // 資源釋放
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

    // 🌟 全螢幕長按雷達吹風
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

    override fun onStop() {
        super.onStop()
        SoundManager.stopWind()
        windHandler.removeCallbacks(windRunnable)
    }

    override fun onDestroy() {
        super.onDestroy()
        windHandler.removeCallbacksAndMessages(null)
    }
}