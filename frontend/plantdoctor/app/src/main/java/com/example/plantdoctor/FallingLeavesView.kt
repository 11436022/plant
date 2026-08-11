package com.example.plantdoctor

import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Canvas
import android.graphics.Matrix
import android.graphics.Paint
import android.util.AttributeSet
import android.view.MotionEvent
import android.view.View
import kotlin.math.atan2
import kotlin.math.cos
import kotlin.math.sin
import kotlin.math.sqrt
import kotlin.random.Random

class FallingLeavesView @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
    defStyleAttr: Int = 0
) : View(context, attrs, defStyleAttr) {

    // 🌟 單個落葉資料結構（包含前後景標記與透明度）
    private data class Leaf(
        var x: Float,
        var y: Float,
        var vx: Float = 0f,           // X軸速度
        var vy: Float = 0f,           // Y軸速度
        var baseSpeedY: Float,        // 下落基礎重力速度
        var rotation: Float,          // 角度
        var rotationSpeed: Float,     // 自轉速度
        var scale: Float,             // 縮放大小
        var swingPhase: Float,        // 左右搖擺相位
        var swingSpeed: Float,        // 左右搖擺頻率
        val isForeground: Boolean,    // 是否為前景葉子
        val alpha: Int,               // 透明度 (0~255)
        val bitmap: Bitmap
    )

    private val leaves = mutableListOf<Leaf>()
    // 🌟 保留你修改的總數量 35 片
    private val maxLeaves = 35
    private val leafBitmaps = mutableListOf<Bitmap>()
    private val paint = Paint(Paint.ANTI_ALIAS_FLAG)

    // 🌟 控制目前繪製模式：前景、背景或全繪製
    var drawLayerMode: LayerMode = LayerMode.ALL

    enum class LayerMode {
        BACKGROUND_ONLY, // 僅繪製背景層（醫生圖片後方）
        FOREGROUND_ONLY, // 僅繪製前景層（醫生圖片前方）
        ALL              // 全繪製
    }

    // 觸控吹風歷史軌跡
    private var lastTouchX = -1f
    private var lastTouchY = -1f

    init {
        // 🌟 確保背景透明，不遮擋底層 gradient_background
        setBackgroundColor(android.graphics.Color.TRANSPARENT)

        // 載入 6 張葉子圖檔（檔名請確保對應 res/drawable）
        val leafResIds = intArrayOf(
            R.drawable.ic_leaf_1,
            R.drawable.ic_leaf_2,
            R.drawable.ic_leaf_3,
            R.drawable.ic_leaf_4,
            R.drawable.ic_leaf_5,
            R.drawable.ic_leaf_6
        )

        for (resId in leafResIds) {
            try {
                val b = BitmapFactory.decodeResource(resources, resId)
                if (b != null) {
                    // 縮放到適當的大小（以 80px 為基準）
                    val scaled = Bitmap.createScaledBitmap(b, 80, 80, true)
                    leafBitmaps.add(scaled)
                }
            } catch (e: Exception) {
                e.printStackTrace()
            }
        }
    }

    override fun onSizeChanged(w: Int, h: Int, oldw: Int, oldh: Int) {
        super.onSizeChanged(w, h, oldw, oldh)
        if (leafBitmaps.isNotEmpty() && leaves.isEmpty()) {
            // 初始化葉子（隨機分散在畫面頂部與上方）
            for (i in 0 until maxLeaves) {
                leaves.add(generateLeaf(w, h, isInitial = true))
            }
        }
    }

    private fun generateLeaf(width: Int, height: Int, isInitial: Boolean = false): Leaf {
        val bitmap = leafBitmaps[Random.nextInt(leafBitmaps.size)]
        val startY = if (isInitial) Random.nextFloat() * height else -100f

        // 隨機分配 50% 幾率為前景或背景葉子
        val isFg = Random.nextBoolean()

        // 🌟 完全採用你剛調整的精準物理數值，並依據前後景做比例與速度加權
        val speedFactor = if (isFg) 1.0f else 0.7f
        val scaleFactor = if (isFg) 1.0f else 0.65f

        return Leaf(
            x = Random.nextFloat() * width,
            y = startY,
            vx = 0f,
            vy = 0f,
            // 保留你的 speed (4~14)，背景葉子稍慢
            baseSpeedY = (Random.nextFloat() * 10f + 4f) * speedFactor,
            rotation = Random.nextFloat() * 360f,
            // 保留你的自轉速度範圍
            rotationSpeed = Random.nextFloat() * 0.6f - 0.3f,
            // 保留你的 scale (0.8~2.2)，背景葉子按比例微調，景深感更逼真
            scale = (Random.nextFloat() * 1.4f + 0.8f) * scaleFactor,
            swingPhase = Random.nextFloat() * 6.28f,
            swingSpeed = Random.nextFloat() * 0.05f + 0.02f,
            isForeground = isFg,
            // 前景不透明 (255)，背景輕微半透明 (180)
            alpha = if (isFg) 255 else 180,
            bitmap = bitmap
        )
    }

    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)
        if (width == 0 || height == 0 || leafBitmaps.isEmpty()) return

        val matrix = Matrix()

        for (leaf in leaves) {
            // 🌟 根據指定模式進行圖層過濾繪製
            if (drawLayerMode == LayerMode.BACKGROUND_ONLY && leaf.isForeground) continue
            if (drawLayerMode == LayerMode.FOREGROUND_ONLY && !leaf.isForeground) continue

            // 1. 物理運動計算（左右搖擺飄落）
            leaf.swingPhase += leaf.swingSpeed
            val swingX = sin(leaf.swingPhase) * 1.5f

            leaf.x += leaf.vx + swingX
            leaf.y += leaf.vy + leaf.baseSpeedY
            leaf.rotation += leaf.rotationSpeed

            // 空氣阻力衰減（平移與自轉衰減）
            leaf.vx *= 0.92f
            leaf.vy *= 0.92f
            leaf.rotationSpeed *= 0.95f

            // 2. 邊界檢查：飄出底部或左右兩側時重置到頂部重新飄落
            if (leaf.y > height + 100 || leaf.x < -100 || leaf.x > width + 100) {
                val newLeaf = generateLeaf(width, height)
                leaf.x = newLeaf.x
                leaf.y = newLeaf.y
                leaf.vx = 0f
                leaf.vy = 0f
                leaf.baseSpeedY = newLeaf.baseSpeedY
                leaf.rotation = newLeaf.rotation
            }

            // 3. 繪製葉子
            matrix.reset()
            matrix.postScale(leaf.scale, leaf.scale)
            matrix.postRotate(leaf.rotation, (leaf.bitmap.width * leaf.scale) / 2f, (leaf.bitmap.height * leaf.scale) / 2f)
            matrix.postTranslate(leaf.x, leaf.y)

            paint.alpha = leaf.alpha
            canvas.drawBitmap(leaf.bitmap, matrix, paint)
        }

        // 持續刷新動畫（60FPS）
        invalidate()
    }

    /**
     * 外部滑動事件注入：當使用者手指滑過時產生風力推開落葉
     */
    fun onTouchEventHandled(event: MotionEvent) {
        val touchX = event.x
        val touchY = event.y

        when (event.action) {
            MotionEvent.ACTION_DOWN -> {
                lastTouchX = touchX
                lastTouchY = touchY
            }
            MotionEvent.ACTION_MOVE -> {
                val dx = touchX - lastTouchX
                val dy = touchY - lastTouchY
                val swipeSpeed = sqrt(dx * dx + dy * dy) // 算出手指划動速度

                if (swipeSpeed > 5f) {
                    val radius = 250f // 風力感應半徑

                    for (leaf in leaves) {
                        val distx = leaf.x - touchX
                        val disty = leaf.y - touchY
                        val distance = sqrt(distx * distx + disty * disty)

                        // 落在風力圈內 -> 計算排斥力
                        if (distance < radius && distance > 0) {
                            val angle = atan2(disty, distx)
                            val force = ((radius - distance) / radius) * (swipeSpeed * 0.8f)

                            leaf.vx += cos(angle) * force
                            leaf.vy += sin(angle) * force
                            leaf.rotationSpeed += (Random.nextFloat() - 0.5f) * 2f
                        }
                    }
                }
                lastTouchX = touchX
                lastTouchY = touchY
            }
            MotionEvent.ACTION_UP, MotionEvent.ACTION_CANCEL -> {
                lastTouchX = -1f
                lastTouchY = -1f
            }
        }
    }
}