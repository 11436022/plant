package com.example.plantdoctor

import android.Manifest
import android.app.Activity
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Bundle
import android.os.Environment
import android.provider.MediaStore
import android.util.Log
import android.widget.Button
import android.widget.ImageButton
import android.widget.ImageView
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import androidx.core.content.FileProvider
import com.bumptech.glide.Glide
import java.io.File
import java.text.SimpleDateFormat
import java.util.*

class UploadActivity : AppCompatActivity() {

    private var selectedImageUri: Uri? = null
    private lateinit var imgPreview: ImageView
    private var photoFile: File? = null

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

        imgPreview = findViewById(R.id.img_preview)
        val btnBack = findViewById<ImageButton>(R.id.btn_back_home)
        val btnCamera = findViewById<Button>(R.id.btn_camera)
        val btnAlbum = findViewById<Button>(R.id.btn_album)
        val btnAnalyze = findViewById<Button>(R.id.btn_analyze)

        imgPreview.setOnClickListener { openAlbum() }
        btnAlbum.setOnClickListener { openAlbum() }
        btnBack.setOnClickListener { finish() }

        // 修改：點擊拍照時先檢查權限
        btnCamera.setOnClickListener {
            checkCameraPermission()
        }

        btnAnalyze.setOnClickListener {
            if (selectedImageUri != null) {
                val sharedPref = getSharedPreferences("PlantDoctor", Context.MODE_PRIVATE)
                val token = sharedPref.getString("token", null)

                if (token.isNullOrEmpty()) {
                    val intent = Intent(this, LoginActivity::class.java)
                    intent.flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
                    startActivity(intent)
                    return@setOnClickListener
                }

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

    private fun updateImagePreview(uri: Uri) {
        selectedImageUri = uri
        // 使用 Glide 來安全地載入圖片，避免因圖片過大造成記憶體溢出 (OutOfMemoryError)
        Glide.with(this)
            .load(uri)
            .centerCrop() // 將圖片置中裁剪以填滿視圖
            .into(imgPreview)
    }
}