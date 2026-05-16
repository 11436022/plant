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

class MainActivity : AppCompatActivity() {

    private val mainHandler = Handler(Looper.getMainLooper())
    private val players = ArrayList<MediaPlayer>()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        // 1. 初始化全域音效管理員
        SoundManager.init(this)

        val tvZhi = findViewById<TextView>(R.id.tv_zhi)
        val tvYe = findViewById<TextView>(R.id.tv_ye)
        val tvShen = findViewById<TextView>(R.id.tv_shen)
        val tvYi = findViewById<TextView>(R.id.tv_yi)

        // 2. 啟動非同步預載與整齊敲擊順序
        prepareAndStartSequence(tvZhi, tvYe, tvShen, tvYi)

        // 3. 🌟 核心修改：在第 1.6 秒（第四下木魚敲完後），音樂無縫接續流淌出來！
        mainHandler.postDelayed({
            SoundManager.startBGM()
        }, 1600)

        // 4. 頁面跳轉邏輯
        mainHandler.postDelayed({
            val sharedPref = getSharedPreferences("PlantDoctor", Context.MODE_PRIVATE)
            val token = sharedPref.getString("token", null)

            if (token != null) {
                val intent = Intent(this, HomeActivity::class.java)
                startActivity(intent)
            } else {
                val intent = Intent(this, IntroActivity::class.java)
                startActivity(intent)
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
                // 🌟 核心修改：將第一個木魚的音量降低 65% (設定為 0.35f)
                mp.setVolume(0.35f, 0.35f)
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

            // 🌟 核心修改：將第二、三、四個木魚的音量同樣降低 65% (設定為 0.35f)
            mediaPlayer.setVolume(0.35f, 0.35f)

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