package com.example.plantdoctor

import android.content.Context
import android.content.Intent
import android.media.MediaPlayer
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.view.animation.OvershootInterpolator
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import androidx.constraintlayout.widget.ConstraintLayout // 🌟 新增

class MainActivity : AppCompatActivity() {

    private val mainHandler = Handler(Looper.getMainLooper())
    private val players = ArrayList<MediaPlayer>()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        // 1. 初始化全域音效管理員（此時會自動去讀取本地 SharedPreferences 儲存的音量）
        SoundManager.init(this)

        // 🌟 核心新增：抓取開機畫面的最外層佈局，讓它能跟著主題變色
        val mainRoot = findViewById<ConstraintLayout>(R.id.main_root_layout)

        val tvZhi = findViewById<TextView>(R.id.tv_zhi)
        val tvYe = findViewById<TextView>(R.id.tv_ye)
        val tvShen = findViewById<TextView>(R.id.tv_shen)
        val tvYi = findViewById<TextView>(R.id.tv_yi)

        // 🌟 核心新增：直接呼叫大總管！把背景和四個木魚大字一起丟進去同步變色
        ThemeManager.applyTheme(
            context = this,
            rootLayout = mainRoot,
            titles = listOf(tvZhi, tvYe, tvShen, tvYi) // 這四個字會自動換成該主題的深色系字體
        )

        // 2. 啟動非同步預載與整齊敲擊順序
        prepareAndStartSequence(tvZhi, tvYe, tvShen, tvYi)

        // 3. 在第 1.6 秒（第四下木魚敲完後），音樂無縫接續流淌出來！
        mainHandler.postDelayed({
            SoundManager.startBGM()
        }, 1600)

        // 4. 頁面跳轉智慧邏輯
        mainHandler.postDelayed({
            val sharedPref = getSharedPreferences("PlantDoctor", Context.MODE_PRIVATE)

            // 讀取兩個獨立的指標
            val isFirstOpen = sharedPref.getBoolean("is_first_open", true) // 預設沒開過，是 true
            val token = sharedPref.getString("token", null)

            if (isFirstOpen) {
                // 1. 如果是全新下載、第一次打開 APP -> 去介紹頁
                val intent = Intent(this, IntroActivity::class.java)
                startActivity(intent)
            } else {
                // 2. 不是第一次開了（看過介紹了）-> 檢查登入狀態
                if (token != null) {
                    // 已登入 -> 去首頁
                    val intent = Intent(this, HomeActivity::class.java)
                    startActivity(intent)
                } else {
                    // 未登入（或剛登出）-> 直接去登入頁，不要再去介紹頁鬧了！
                    val intent = Intent(this, LoginActivity::class.java)
                    startActivity(intent)
                }
            }
            finish()
        }, 3800) // 稍微延長一點留白時間，讓背景音樂在開機畫面鋪墊得更優雅
    }

    private fun prepareAndStartSequence(tvZhi: TextView, tvYe: TextView, tvShen: TextView, tvYi: TextView) {
        try {
            val afd = assets.openFd("muyu_do.mp3")
            val firstPlayer = MediaPlayer()
            firstPlayer.setDataSource(afd.fileDescriptor, afd.startOffset, afd.length)
            afd.close()

            firstPlayer.setOnPreparedListener { mp ->
                // 讀取 SoundManager 中使用者設定好的「開 APP 音效音量」
                val currentVol = SoundManager.getStartAppVolume()
                mp.setVolume(currentVol, currentVol)

                mp.start()
                players.add(mp)

                bounceTextView(tvZhi)
                startRemainingSequence(tvYe, tvShen, tvYi)
            }
            firstPlayer.prepareAsync()

        } catch (e: Exception) {
            e.printStackTrace()
            startRemainingSequence(tvYe, tvShen, tvYi)
        }
    }

    private fun startRemainingSequence(tvYe: TextView, tvShen: TextView, tvYi: TextView) {
        val interval = 400L
        mainHandler.postDelayed({ playToneAndBounce(tvYe, "muyu_mi.mp3") }, 1 * interval)
        mainHandler.postDelayed({ playToneAndBounce(tvShen, "muyu_so.mp3") }, 2 * interval)
        mainHandler.postDelayed({ playToneAndBounce(tvYi, "muyu_do5.mp3") }, 3 * interval)
    }

    private fun playToneAndBounce(textView: TextView, assetName: String) {
        try {
            val afd = assets.openFd(assetName)
            val mediaPlayer = MediaPlayer()
            mediaPlayer.setDataSource(afd.fileDescriptor, afd.startOffset, afd.length)
            afd.close()
            mediaPlayer.prepare()

            // 同樣讀取 SoundManager 中最新設定的開 APP 音量，不再寫死
            val currentVol = SoundManager.getStartAppVolume()
            mediaPlayer.setVolume(currentVol, currentVol)

            mediaPlayer.start()
            players.add(mediaPlayer)
        } catch (e: Exception) {
            e.printStackTrace()
        }
        bounceTextView(textView)
    }

    private fun bounceTextView(textView: TextView) {
        mainHandler.postDelayed({
            textView.animate()
                .translationY(-30f)
                .setDuration(150)
                .setInterpolator(OvershootInterpolator())
                .withEndAction {
                    textView.animate().translationY(0f).setDuration(100).start()
                }.start()
        }, 50)
    }

    override fun onDestroy() {
        super.onDestroy()
        mainHandler.removeCallbacksAndMessages(null)
        // 這裡千萬不要釋放或停止全域的背景音樂，只要清空木魚的 MediaPlayer 即可
        for (player in players) {
            try {
                player.stop()
                player.release()
            } catch (e: Exception) { }
        }
        players.clear()
    }
}