package com.example.plantdoctor

import android.content.Context
import android.graphics.*
import android.util.AttributeSet
import android.view.MotionEvent
import android.view.View
import kotlin.math.max
import kotlin.math.min

class InteractiveBoxView @JvmOverloads constructor(
    context: Context, attrs: AttributeSet? = null
) : View(context, attrs) {

    private val cropZones = mutableListOf<CropZone>()
    private var isEditable = true // 是否允許使用者手勢調整 (單植物時設為 false)

    // 畫筆設定
    private val boxPaint = Paint().apply {
        color = Color.parseColor("#FF6D00") // 鮮豔橘色外框
        style = Paint.Style.STROKE
        strokeWidth = 8f
        isAntiAlias = true
    }

    private val handlePaint = Paint().apply {
        color = Color.WHITE // 控制角圓點顏色
        style = Paint.Style.FILL
        isAntiAlias = true
    }

    private val textBgPaint = Paint().apply {
        color = Color.parseColor("#80000000") // 半透明黑色文字背景
        style = Paint.Style.FILL
    }

    private val textPaint = Paint().apply {
        color = Color.WHITE
        textSize = 36f
        isFakeBoldText = true
        isAntiAlias = true
    }

    // 手勢控制相關變數
    private var selectedZone: CropZone? = null
    private var activeTouchMode = TouchMode.NONE
    private var lastTouchX = 0f
    private var lastTouchY = 0f
    private val handleRadius = 24f // 四個角落拖動點的觸控半徑

    private enum class TouchMode {
        NONE, MOVE, RESIZE_TL, RESIZE_TR, RESIZE_BL, RESIZE_BR
    }

    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)
        val w = width.toFloat()
        val h = height.toFloat()

        cropZones.forEach { zone ->
            if (!zone.isEnabled) return@forEach

            // 歸一化座標 (0.0~1.0) 轉 實際像素 (px)
            val rect = RectF(
                zone.rectNorm.left * w,
                zone.rectNorm.top * h,
                zone.rectNorm.right * w,
                zone.rectNorm.bottom * h
            )

            // 1. 畫外框
            canvas.drawRect(rect, boxPaint)

            // 2. 如果可編輯，畫出四角控制點 (白色圓點)
            if (isEditable) {
                canvas.drawCircle(rect.left, rect.top, handleRadius, handlePaint)
                canvas.drawCircle(rect.right, rect.top, handleRadius, handlePaint)
                canvas.drawCircle(rect.left, rect.bottom, handleRadius, handlePaint)
                canvas.drawCircle(rect.right, rect.bottom, handleRadius, handlePaint)
            }

            // 3. 畫標籤文字背景與名稱
            // InteractiveBoxView.kt onDraw 內部
            val labelText = if (zone.intervalMinutes > 0) "${zone.name} (${zone.intervalMinutes}s)" else zone.name
            val textWidth = textPaint.measureText(labelText)
            val bgRect = RectF(
                rect.left,
                rect.top - 45f,
                rect.left + textWidth + 20f,
                rect.top
            )
            canvas.drawRect(bgRect, textBgPaint)
            canvas.drawText(labelText, rect.left + 10f, rect.top - 10f, textPaint)
        }
    }

    override fun onTouchEvent(event: MotionEvent): Boolean {
        // 如果設為不可編輯（如單植物模式），直接不處理手勢
        if (!isEditable) return super.onTouchEvent(event)

        val x = event.x
        val y = event.y
        val w = width.toFloat()
        val h = height.toFloat()

        if (w == 0f || h == 0f) return false

        when (event.action) {
            MotionEvent.ACTION_DOWN -> {
                selectedZone = null
                activeTouchMode = TouchMode.NONE

                // 檢查是否點擊到某個區域或角落控制點
                for (zone in cropZones.reversed()) {
                    val rect = RectF(
                        zone.rectNorm.left * w,
                        zone.rectNorm.top * h,
                        zone.rectNorm.right * w,
                        zone.rectNorm.bottom * h
                    )

                    // 1. 檢查四個角落
                    val touchRadius = handleRadius * 2f
                    when {
                        isNearPoint(x, y, rect.left, rect.top, touchRadius) -> {
                            selectedZone = zone
                            activeTouchMode = TouchMode.RESIZE_TL
                        }
                        isNearPoint(x, y, rect.right, rect.top, touchRadius) -> {
                            selectedZone = zone
                            activeTouchMode = TouchMode.RESIZE_TR
                        }
                        isNearPoint(x, y, rect.left, rect.bottom, touchRadius) -> {
                            selectedZone = zone
                            activeTouchMode = TouchMode.RESIZE_BL
                        }
                        isNearPoint(x, y, rect.right, rect.bottom, touchRadius) -> {
                            selectedZone = zone
                            activeTouchMode = TouchMode.RESIZE_BR
                        }
                        rect.contains(x, y) -> { // 2. 點擊內部移動整個框
                            selectedZone = zone
                            activeTouchMode = TouchMode.MOVE
                        }
                    }

                    if (selectedZone != null) break
                }

                lastTouchX = x
                lastTouchY = y
                return selectedZone != null
            }

            MotionEvent.ACTION_MOVE -> {
                val zone = selectedZone ?: return false
                val dx = (x - lastTouchX) / w
                val dy = (y - lastTouchY) / h

                val norm = zone.rectNorm
                val minSize = 0.1f // 限制框框最小尺寸，避免縮到消失

                when (activeTouchMode) {
                    TouchMode.MOVE -> {
                        // 確保移動時不超出畫面
                        val widthNorm = norm.width()
                        val heightNorm = norm.height()

                        var newLeft = norm.left + dx
                        var newTop = norm.top + dy

                        newLeft = max(0f, min(newLeft, 1f - widthNorm))
                        newTop = max(0f, min(newTop, 1f - heightNorm))

                        norm.set(newLeft, newTop, newLeft + widthNorm, newTop + heightNorm)
                    }
                    TouchMode.RESIZE_TL -> {
                        norm.left = min(max(0f, norm.left + dx), norm.right - minSize)
                        norm.top = min(max(0f, norm.top + dy), norm.bottom - minSize)
                    }
                    TouchMode.RESIZE_TR -> {
                        norm.right = max(min(1f, norm.right + dx), norm.left + minSize)
                        norm.top = min(max(0f, norm.top + dy), norm.bottom - minSize)
                    }
                    TouchMode.RESIZE_BL -> {
                        norm.left = min(max(0f, norm.left + dx), norm.right - minSize)
                        norm.bottom = max(min(1f, norm.bottom + dy), norm.top + minSize)
                    }
                    TouchMode.RESIZE_BR -> {
                        norm.right = max(min(1f, norm.right + dx), norm.left + minSize)
                        norm.bottom = max(min(1f, norm.bottom + dy), norm.top + minSize)
                    }
                    else -> {}
                }

                lastTouchX = x
                lastTouchY = y
                invalidate() // 即時刷新畫面
                return true
            }

            MotionEvent.ACTION_UP, MotionEvent.ACTION_CANCEL -> {
                // ⭕【新增於此】：當手指抬起或取消時，如果剛才正在拖移/縮放框框，立刻通知 Activity 儲存最新位置
                if (selectedZone != null && activeTouchMode != TouchMode.NONE) {
                    (context as? WebcamActivity)?.onCropZonesChanged()
                }

                activeTouchMode = TouchMode.NONE
                selectedZone = null
                return true
            }
        }
        return super.onTouchEvent(event)
    }

    private fun isNearPoint(x: Float, y: Float, px: Float, py: Float, radius: Float): Boolean {
        val dx = x - px
        val dy = y - py
        return (dx * dx + dy * dy) <= (radius * radius)
    }

    /**
     * 更新並重繪畫面上所有的 CropZone 框框
     */
    fun updateZones(zones: List<CropZone>, editable: Boolean = true) {
        this.isEditable = editable
        cropZones.clear()
        cropZones.addAll(zones)
        invalidate()
    }
}