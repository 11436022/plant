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

    private var isFirstLaunch = true

    // 🌟 核心變數：儲存各軌音量
    private var volStartApp = 0.7f
    private var volBgm = 0.7f
    private var volBubble = 0.7f
    private var volWind = 0.7f

    fun init(context: Context) {
        if (soundPool != null) return

        val appContext = context.applicationContext

        // 初始化時讀取進度條設定
        val sharedPref = appContext.getSharedPreferences("PlantDoctor", Context.MODE_PRIVATE)
        volStartApp = sharedPref.getInt("VOL_START_APP", 35) / 100f
        volBgm = sharedPref.getInt("VOL_BGM", 70) / 100f
        volBubble = sharedPref.getInt("VOL_BUBBLE", 70) / 100f
        volWind = sharedPref.getInt("VOL_WIND", 70) / 100f

        ProcessLifecycleOwner.get().lifecycle.addObserver(this)

        // === [A] SoundPool ===
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

        // === [B] 風聲 ===
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
            windPlayer?.setVolume(volWind, volWind)
        } catch (e: Exception) {
            e.printStackTrace()
        }

        // === [C] 背景音樂 ===
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
            bgmPlayer?.setVolume(volBgm, volBgm)
        } catch (e: Exception) {
            e.printStackTrace()
        }
    }

    // 🌟 核心新增：讓外界播放開 APP 音效（如木魚）的地方可以獲取目前設定的音量（回傳 0.0f ~ 1.0f）
    fun getStartAppVolume(): Float {
        return volStartApp
    }

    fun setStartAppVolume(volume: Float) {
        this.volStartApp = volume
    }

    fun setBgmVolume(volume: Float) {
        this.volBgm = volume
        if (bgmPlayer != null && bgmPlayer!!.isPlaying) {
            bgmPlayer?.setVolume(volume, volume)
        }
    }

    fun setBubbleVolume(volume: Float) {
        this.volBubble = volume
    }

    fun setWindVolume(volume: Float) {
        this.volWind = volume
        windPlayer?.setVolume(volume, volume)
    }

    fun startBGM() {
        isFirstLaunch = false
        if (bgmPlayer != null && !bgmPlayer!!.isPlaying) {
            bgmPlayer?.setVolume(volBgm, volBgm)
            bgmPlayer?.start()
        }
    }

    override fun onStart(owner: LifecycleOwner) {
        super.onStart(owner)
        if (isFirstLaunch) return
        if (bgmPlayer != null && !bgmPlayer!!.isPlaying) {
            bgmPlayer?.setVolume(volBgm, volBgm)
            bgmPlayer?.start()
        }
    }

    override fun onStop(owner: LifecycleOwner) {
        super.onStop(owner)
        isFirstLaunch = false
        if (bgmPlayer != null && bgmPlayer!!.isPlaying) {
            bgmPlayer?.pause()
        }
    }

    fun playBubblePop() {
        if (isSoundPoolLoaded && soundPool != null) {
            val randomIndex = random.nextInt(4)
            soundPool?.play(popSoundIds[randomIndex], volBubble, volBubble, 1, 0, 1.0f)
        }
    }

    fun startWind() {
        if (windPlayer != null && !windPlayer!!.isPlaying) {
            windPlayer?.setVolume(volWind, volWind)
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