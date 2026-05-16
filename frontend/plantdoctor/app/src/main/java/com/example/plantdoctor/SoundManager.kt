package com.example.plantdoctor

import android.content.Context
import android.media.AudioAttributes
import android.media.AudioManager
import android.media.MediaPlayer
import android.media.SoundPool
import android.util.Log
import androidx.lifecycle.DefaultLifecycleObserver
import androidx.lifecycle.LifecycleOwner
import androidx.lifecycle.ProcessLifecycleOwner
import java.util.Random

object SoundManager : DefaultLifecycleObserver {

    private var soundPool: SoundPool? = null
    private val popSoundIds = IntArray(4)
    private var isSoundPoolLoaded = false
    private val random = Random()

    private var windPlayer: MediaPlayer? = null
    private var bgmPlayer: MediaPlayer? = null

    // 🌟 核心防禦：增加一個防搶跑開關，預設為 true（代表正在執行開機木魚交響樂）
    private var isFirstLaunch = true

    fun init(context: Context) {
        if (soundPool != null) return

        val appContext = context.applicationContext

        ProcessLifecycleOwner.get().lifecycle.addObserver(this)

        // === [A] 初始化 SoundPool ===
        val audioAttributes = AudioAttributes.Builder()
            .setUsage(AudioAttributes.USAGE_GAME)
            .setContentType(AudioAttributes.CONTENT_TYPE_SONIFICATION)
            .build()

        soundPool = SoundPool.Builder()
            .setMaxStreams(5)
            .setAudioAttributes(audioAttributes)
            .build()

        var loadCounter = 0
        soundPool?.setOnLoadCompleteListener { _, _, status ->
            if (status == 0) {
                loadCounter++
                if (loadCounter == 4) {
                    isSoundPoolLoaded = true
                }
            }
        }

        try {
            val afd1 = appContext.assets.openFd("pop1.mp3")
            val afd2 = appContext.assets.openFd("pop2.mp3")
            val afd3 = appContext.assets.openFd("pop3.mp3")
            val afd4 = appContext.assets.openFd("pop4.mp3")

            popSoundIds[0] = soundPool?.load(afd1, 1) ?: 0
            popSoundIds[1] = soundPool?.load(afd2, 1) ?: 0
            popSoundIds[2] = soundPool?.load(afd3, 1) ?: 0
            popSoundIds[3] = soundPool?.load(afd4, 1) ?: 0

            afd1.close()
            afd2.close()
            afd3.close()
            afd4.close()
        } catch (e: Exception) {
            e.printStackTrace()
        }

        // === [B] 初始化風聲 ===
        try {
            val assetFileDescriptor = appContext.assets.openFd("wind.mp3")
            windPlayer = MediaPlayer()
            windPlayer?.setAudioStreamType(AudioManager.STREAM_MUSIC)
            windPlayer?.setDataSource(
                assetFileDescriptor.fileDescriptor,
                assetFileDescriptor.startOffset,
                assetFileDescriptor.length
            )
            assetFileDescriptor.close()
            windPlayer?.isLooping = true
            windPlayer?.prepare()
        } catch (e: Exception) {
            e.printStackTrace()
        }

        // === [C] 初始化背景音樂 ===
        try {
            val assetFileDescriptor = appContext.assets.openFd("forest.mp3")
            bgmPlayer = MediaPlayer()
            bgmPlayer?.setAudioStreamType(AudioManager.STREAM_MUSIC)
            bgmPlayer?.setDataSource(
                assetFileDescriptor.fileDescriptor,
                assetFileDescriptor.startOffset,
                assetFileDescriptor.length
            )
            assetFileDescriptor.close()
            bgmPlayer?.isLooping = true
            bgmPlayer?.prepare()
            bgmPlayer?.setVolume(1.0f, 1.0f)
        } catch (e: Exception) {
            e.printStackTrace()
        }
    }

    // 🌟 手動啟動背景音樂的方法
    fun startBGM() {
        // 只要手動叫音樂響起，就代表開機木魚時間結束了，解除防線
        isFirstLaunch = false
        if (bgmPlayer != null && !bgmPlayer!!.isPlaying) {
            bgmPlayer?.start()
        }
    }

    // 🌟 當整個 App 回到前台時
    override fun onStart(owner: LifecycleOwner) {
        super.onStart(owner)

        // 🌟 核心修正：如果是「第一次開機點開 App」，全域攔截器不准偷放音樂！把舞台留給木魚！
        if (isFirstLaunch) {
            Log.d("SoundManager", "🛑 檢測到冷啟動開機，攔截自動播放音樂，保留木魚獨奏。")
            return
        }

        if (bgmPlayer != null && !bgmPlayer!!.isPlaying) {
            bgmPlayer?.start()
            Log.d("SoundManager", "📱 App 從後台回來，自動恢復背景音樂")
        }
    }

    // 🌟 當整個 App 退到手機桌面時
    override fun onStop(owner: LifecycleOwner) {
        super.onStop(owner)
        // 使用者退到桌面了，下一次再進來時肯定不是冷啟動了，安全關閉開關
        isFirstLaunch = false
        if (bgmPlayer != null && bgmPlayer!!.isPlaying) {
            bgmPlayer?.pause()
            Log.d("SoundManager", "🏠 User 回到手機桌面，自動暫停背景音樂")
        }
    }

    fun playBubblePop() {
        if (isSoundPoolLoaded && soundPool != null) {
            val randomIndex = random.nextInt(4)
            soundPool?.play(popSoundIds[randomIndex], 1.0f, 1.0f, 1, 0, 1.0f)
        }
    }

    fun startWind() {
        if (windPlayer != null && !windPlayer!!.isPlaying) {
            windPlayer?.start()
        }
    }

    fun stopWind() {
        if (windPlayer != null && windPlayer!!.isPlaying) {
            windPlayer?.pause()
            windPlayer?.seekTo(0)
        }
    }

    fun release() {
        soundPool?.release()
        soundPool = null
        windPlayer?.release()
        windPlayer = null
        bgmPlayer?.release()
        bgmPlayer = null
        isSoundPoolLoaded = false
        isFirstLaunch = true
    }
}