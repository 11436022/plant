package com.example.plantdoctor

import android.app.Activity
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.widget.Button
import android.widget.ImageButton
import android.widget.ImageView
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity

class UploadActivity : AppCompatActivity() {

    private var selectedImageUri: Uri? = null
    private lateinit var imgPreview: ImageView

    private val selectImageLauncher = registerForActivityResult(ActivityResultContracts.StartActivityForResult()) { result ->
        if (result.resultCode == Activity.RESULT_OK) {
            val uri = result.data?.data
            if (uri != null) {
                try {
                    val takeFlags: Int = Intent.FLAG_GRANT_READ_URI_PERMISSION
                    contentResolver.takePersistableUriPermission(uri, takeFlags)
                } catch (e: Exception) { }

                selectedImageUri = uri
                imgPreview.setImageURI(uri)
                imgPreview.scaleType = ImageView.ScaleType.CENTER_CROP
                Toast.makeText(this, "照片已成功選取！", Toast.LENGTH_SHORT).show()
            }
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

        btnCamera.setOnClickListener {
            Toast.makeText(this, "相機功能開發中...", Toast.LENGTH_SHORT).show()
        }

        btnAnalyze.setOnClickListener {
            if (selectedImageUri != null) {
                // --- 核心修正：清理 Token ---
                val sharedPref = getSharedPreferences("PlantDoctor", Context.MODE_PRIVATE)
                val rawToken = sharedPref.getString("token", "") ?: ""

                // 強制去除可能導致 "Invalid header padding" 的換行符或空白
                val cleanToken = rawToken.replace("\n", "").replace("\r", "").trim()

                if (cleanToken.isEmpty()) {
                    Toast.makeText(this, "登入已失效，請重新登入", Toast.LENGTH_SHORT).show()
                    startActivity(Intent(this, LoginActivity::class.java))
                    return@setOnClickListener
                }

                // 將乾淨的 Token 傳給分析畫面
                val intent = Intent(this, DiagnoseProgressActivity::class.java)
                intent.putExtra("IMAGE_URI", selectedImageUri.toString())
                intent.putExtra("CLEAN_TOKEN", cleanToken)
                startActivity(intent)
            } else {
                Toast.makeText(this, "請先選擇一張照片", Toast.LENGTH_SHORT).show()
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
}