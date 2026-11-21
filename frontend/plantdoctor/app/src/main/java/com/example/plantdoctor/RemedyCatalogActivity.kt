package com.example.plantdoctor

import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.text.Editable
import android.text.TextWatcher
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.*
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.recyclerview.widget.GridLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.bumptech.glide.Glide
import com.bumptech.glide.load.resource.bitmap.CenterCrop
import com.bumptech.glide.load.resource.bitmap.RoundedCorners
import retrofit2.Call
import retrofit2.Callback
import retrofit2.Response

class RemedyCatalogActivity : AppCompatActivity() {

    private lateinit var btnBackHome: ImageButton
    private lateinit var etSearchRemedy: EditText
    private lateinit var btnClearSearch: ImageView

    // 4 大主題解決專區 Chips
    private lateinit var chipAll: TextView
    private lateinit var chipDisease: TextView
    private lateinit var chipPest: TextView
    private lateinit var chipGrowth: TextView
    private lateinit var chipPetSafe: TextView

    private lateinit var tvCountLabel: TextView
    private lateinit var pbLoading: ProgressBar
    private lateinit var layoutEmptyState: LinearLayout
    private lateinit var rvRemedies: RecyclerView

    private lateinit var remedyAdapter: RemedyAdapter
    private val remedyList = mutableListOf<RemedyItem>()
    private var currentCategory = "all"
    private var currentQuery = ""
    private val searchHandler = Handler(Looper.getMainLooper())
    private var searchRunnable: Runnable? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_remedy_catalog)

        initViews()
        setupListeners()
        setupRecyclerView()

        // 檢查是否由診斷結果頁或病歷詳情頁攜帶搜尋字串前來
        val initialQuery = intent.getStringExtra("EXTRA_SEARCH_QUERY") ?: intent.getStringExtra("AUTO_QUERY")
        if (!initialQuery.isNullOrBlank()) {
            etSearchRemedy.setText(initialQuery)
            currentQuery = initialQuery
        }

        fetchRemedies()
    }

    private fun initViews() {
        btnBackHome = findViewById(R.id.btn_back_home)
        etSearchRemedy = findViewById(R.id.et_search_remedy)
        btnClearSearch = findViewById(R.id.btn_clear_search)

        chipAll = findViewById(R.id.chip_all)
        chipDisease = findViewById(R.id.chip_disease)
        chipPest = findViewById(R.id.chip_pest)
        chipGrowth = findViewById(R.id.chip_growth)
        chipPetSafe = findViewById(R.id.chip_pet_safe)

        tvCountLabel = findViewById(R.id.tv_count_label)
        pbLoading = findViewById(R.id.pb_loading)
        layoutEmptyState = findViewById(R.id.layout_empty_state)
        rvRemedies = findViewById(R.id.rv_remedies)
    }

    private fun setupListeners() {
        btnBackHome.setOnClickListener {
            SoundManager.playBubblePop()
            finish()
        }

        btnClearSearch.setOnClickListener {
            SoundManager.playBubblePop()
            etSearchRemedy.setText("")
        }

        // 搜尋輸入防抖動監聽 (Debounce 350ms)
        etSearchRemedy.addTextChangedListener(object : TextWatcher {
            override fun beforeTextChanged(s: CharSequence?, start: Int, count: Int, after: Int) {}
            override fun onTextChanged(s: CharSequence?, start: Int, before: Int, count: Int) {
                btnClearSearch.visibility = if (s.isNullOrEmpty()) View.GONE else View.VISIBLE
            }
            override fun afterTextChanged(s: Editable?) {
                searchRunnable?.let { searchHandler.removeCallbacks(it) }
                searchRunnable = Runnable {
                    val q = s?.toString()?.trim() ?: ""
                    if (q != currentQuery) {
                        currentQuery = q
                        fetchRemedies()
                    }
                }
                searchHandler.postDelayed(searchRunnable!!, 350)
            }
        })

        // 4 大主題分類 Chip 點選切換
        val chips = listOf(
            chipAll to "all",
            chipDisease to "disease",
            chipPest to "pest",
            chipGrowth to "growth",
            chipPetSafe to "pet_safe"
        )

        chips.forEach { (chipView, cat) ->
            chipView.setOnClickListener {
                SoundManager.playBubblePop()
                if (currentCategory != cat) {
                    currentCategory = cat
                    updateChipStyles()
                    fetchRemedies()
                }
            }
        }
    }

    private fun updateChipStyles() {
        val chips = listOf(
            chipAll to "all",
            chipDisease to "disease",
            chipPest to "pest",
            chipGrowth to "growth",
            chipPetSafe to "pet_safe"
        )
        for ((chipView, cat) in chips) {
            if (cat == currentCategory) {
                chipView.setBackgroundResource(R.drawable.bg_chip_selected)
                chipView.setTextColor(android.graphics.Color.WHITE)
            } else {
                chipView.setBackgroundResource(R.drawable.bg_chip_unselected)
                chipView.setTextColor(android.graphics.Color.parseColor("#37474F"))
            }
        }
    }

    private fun setupRecyclerView() {
        remedyAdapter = RemedyAdapter(
            items = remedyList,
            onItemClick = { item ->
                showRemedyDetailDialog(item)
            },
            onBuyClick = { item ->
                SoundManager.playBubblePop()
                val url = item.purchaseSearchUrl
                if (!url.isNullOrEmpty()) {
                    val intent = Intent(Intent.ACTION_VIEW, Uri.parse(url))
                    startActivity(intent)
                } else {
                    Toast.makeText(this, "查無此商品採購連結", Toast.LENGTH_SHORT).show()
                }
            }
        )
        // 🌟 核心升級：告別單調條列，改採雙欄網格 (2-Column Grid) 排版！
        rvRemedies.layoutManager = GridLayoutManager(this, 2)
        rvRemedies.adapter = remedyAdapter
    }

    private fun fetchRemedies() {
        pbLoading.visibility = View.VISIBLE
        layoutEmptyState.visibility = View.GONE
        tvCountLabel.text = "搜尋臺灣農業部官方審定資材中..."

        val apiService = PlantApiService.create()
        apiService.getRemedies(
            query = if (currentQuery.isBlank()) null else currentQuery,
            category = if (currentCategory == "all") null else currentCategory,
            skip = 0,
            limit = 100
        ).enqueue(object : Callback<RemediesResponse> {
            override fun onResponse(call: Call<RemediesResponse>, response: Response<RemediesResponse>) {
                pbLoading.visibility = View.GONE
                if (response.isSuccessful && response.body() != null) {
                    val data = response.body()!!
                    remedyList.clear()
                    remedyList.addAll(data.items)
                    remedyAdapter.notifyDataSetChanged()

                    tvCountLabel.text = "找到 ${data.total} 筆臺灣官方審定資材（顯示前 ${remedyList.size} 筆）"

                    if (remedyList.isEmpty()) {
                        layoutEmptyState.visibility = View.VISIBLE
                    } else {
                        layoutEmptyState.visibility = View.GONE
                    }
                } else {
                    tvCountLabel.text = "無法載入資材資料 (HTTP ${response.code()})"
                    layoutEmptyState.visibility = View.VISIBLE
                }
            }

            override fun onFailure(call: Call<RemediesResponse>, t: Throwable) {
                pbLoading.visibility = View.GONE
                tvCountLabel.text = "網路連線失敗，請確認後端伺服器運作中"
                layoutEmptyState.visibility = View.VISIBLE
            }
        })
    }

    private fun showRemedyDetailDialog(item: RemedyItem) {
        SoundManager.playBubblePop()

        val dialogView = LayoutInflater.from(this).inflate(R.layout.dialog_remedy_detail, null)
        val dialog = AlertDialog.Builder(this)
            .setView(dialogView)
            .create()

        dialog.window?.setBackgroundDrawableResource(android.R.color.transparent)

        val tvTitle = dialogView.findViewById<TextView>(R.id.dialog_remedy_title)
        val tvSubtitle = dialogView.findViewById<TextView>(R.id.dialog_remedy_subtitle)
        val btnClose = dialogView.findViewById<ImageButton>(R.id.dialog_btn_close)
        val badgeCategory = dialogView.findViewById<TextView>(R.id.dialog_badge_category)
        val badgePet = dialogView.findViewById<TextView>(R.id.dialog_badge_pet)
        val badgeIndoor = dialogView.findViewById<TextView>(R.id.dialog_badge_indoor)
        val tvEfficacy = dialogView.findViewById<TextView>(R.id.dialog_tv_efficacy)
        val tvIngredients = dialogView.findViewById<TextView>(R.id.dialog_tv_ingredients)
        val tvDilution = dialogView.findViewById<TextView>(R.id.dialog_tv_dilution)
        val tvSafetyIndoor = dialogView.findViewById<TextView>(R.id.dialog_tv_safety_indoor)
        val tvSafetyPet = dialogView.findViewById<TextView>(R.id.dialog_tv_safety_pet)
        val btnLicense = dialogView.findViewById<TextView>(R.id.dialog_btn_license)
        val btnBuy = dialogView.findViewById<TextView>(R.id.dialog_btn_buy)

        // 填入資料
        tvTitle.text = item.productName
        val cityStr = if (!item.city.isNullOrEmpty()) " (${item.city})" else ""
        tvSubtitle.text = "${item.registrationNo} · ${item.companyName}$cityStr"

        // 類別標籤
        val catName = item.categoryName ?: "官方免登記資材"
        badgeCategory.text = if (catName.contains("蟲")) "🐛 $catName" else if (catName.contains("病")) "🛡️ $catName" else "🌿 $catName"

        // 寵物安全標籤
        if (item.petFriendlyStatus == "SAFE") {
            badgePet.text = "🐾 寵物友善"
            badgePet.setBackgroundResource(R.drawable.bg_badge_safe)
            badgePet.setTextColor(android.graphics.Color.parseColor("#0277BD"))
        } else {
            badgePet.text = "⚠️ 避開犬貓"
            badgePet.setBackgroundResource(R.drawable.bg_badge_caution)
            badgePet.setTextColor(android.graphics.Color.parseColor("#E65100"))
        }

        // 功效與成分
        tvEfficacy.text = item.efficacySummary ?: "植物生理健康保護與抗逆力提升"
        tvIngredients.text = item.activeIngredient

        // 生活化調配指南（自動依品項微調）
        if (item.productName.contains("免稀釋")) {
            tvDilution.text = "此為「即開即噴免稀釋」配方，搖勻後直接對準病徵處或葉背噴灑即可，免量杯免裝水！"
        } else {
            tvDilution.text = "拿 1 瓶 600ml 寶特瓶裝水，倒入「半瓶蓋」藥劑搖勻即可均勻噴灑於葉背與莖部（免用量杯）。"
        }

        // 安全說明
        val indoorDesc = item.indoorReason ?: "經農業部審定純天然居家安全資材，室內安心使用"
        val petDesc = item.petFriendlyDesc ?: if (item.petFriendlyStatus == "SAFE") "食品級或天然礦物成分，犬貓寵物友善" else "天然植物精油揮發濃度較高，噴灑時建議讓毛孩至其他房間"
        tvSafetyIndoor.text = "• 居家室內：$indoorDesc"
        tvSafetyPet.text = "• 寵物安全：$petDesc"

        // 按鈕點擊
        btnClose.setOnClickListener {
            dialog.dismiss()
        }

        // 審定證件按鈕
        if (!item.licenseImageUrl.isNullOrEmpty()) {
            btnLicense.visibility = View.VISIBLE
            btnLicense.setOnClickListener {
                SoundManager.playBubblePop()
                dialog.dismiss()
                val intent = Intent(this, ImagePreviewActivity::class.java).apply {
                    putExtra("IMAGE_PATH", item.licenseImageUrl)
                }
                startActivity(intent)
            }
        } else {
            btnLicense.visibility = View.GONE
        }

        // 採購比價按鈕
        btnBuy.setOnClickListener {
            SoundManager.playBubblePop()
            dialog.dismiss()
            val url = item.purchaseSearchUrl
            if (!url.isNullOrEmpty()) {
                startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)))
            } else {
                Toast.makeText(this, "查無此商品採購連結", Toast.LENGTH_SHORT).show()
            }
        }

        dialog.show()
    }

    // --- 雙欄商品卡片 Adapter ---
    class RemedyAdapter(
        private val items: List<RemedyItem>,
        private val onItemClick: (RemedyItem) -> Unit,
        private val onBuyClick: (RemedyItem) -> Unit
    ) : RecyclerView.Adapter<RemedyAdapter.ViewHolder>() {

        class ViewHolder(v: View) : RecyclerView.ViewHolder(v) {
            val imgLicense: ImageView = v.findViewById(R.id.img_remedy_license)
            val tvCategoryBadge: TextView = v.findViewById(R.id.tv_category_badge)
            val tvPetBadge: TextView = v.findViewById(R.id.tv_remedy_pet_badge)
            val tvName: TextView = v.findViewById(R.id.tv_remedy_name)
            val tvEfficacy: TextView = v.findViewById(R.id.tv_remedy_efficacy)
            val tvIngredients: TextView = v.findViewById(R.id.tv_remedy_ingredients)
            val btnBuyShopee: TextView = v.findViewById(R.id.btn_buy_shopee)
        }

        override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ViewHolder {
            val view = LayoutInflater.from(parent.context).inflate(R.layout.item_remedy_card, parent, false)
            return ViewHolder(view)
        }

        override fun onBindViewHolder(holder: ViewHolder, position: Int) {
            val item = items[position]

            holder.tvName.text = item.productName
            holder.tvIngredients.text = "🌿 ${item.activeIngredient}"

            // 醒目的核心功效 / 專治適應症標籤
            holder.tvEfficacy.text = item.efficacySummary ?: "🎯 專治：真菌病害與微小害蟲"

            // 類別標籤 (如：🛡️ 殺菌防病 / 🐛 驅蟲除蟎 / 🌱 活力營養)
            val catText = item.categoryName ?: when {
                item.useGrowth == true -> "🌱 活力營養"
                item.useDisease && !item.usePest -> "🛡️ 殺菌防病"
                item.usePest && !item.useDisease -> "🐛 驅蟲除蟎"
                else -> "🛡️🐛 防病抗蟲"
            }
            holder.tvCategoryBadge.text = catText

            // 寵物友善標籤
            when (item.petFriendlyStatus) {
                "SAFE" -> {
                    holder.tvPetBadge.text = "🐾 寵物安全"
                    holder.tvPetBadge.setBackgroundResource(R.drawable.bg_badge_safe)
                    holder.tvPetBadge.setTextColor(android.graphics.Color.parseColor("#2E7D32"))
                }
                "CAUTION" -> {
                    holder.tvPetBadge.text = "⚠️ 避開犬貓"
                    holder.tvPetBadge.setBackgroundResource(R.drawable.bg_badge_caution)
                    holder.tvPetBadge.setTextColor(android.graphics.Color.parseColor("#E65100"))
                }
                else -> {
                    holder.tvPetBadge.text = "🚫 寵物禁忌"
                    holder.tvPetBadge.setBackgroundResource(R.drawable.bg_badge_disease)
                    holder.tvPetBadge.setTextColor(android.graphics.Color.parseColor("#C62828"))
                }
            }

            // 圖片載入 (Glide)
            val imgUrl = item.licenseImageUrl
            if (!imgUrl.isNullOrEmpty()) {
                Glide.with(holder.itemView.context)
                    .load(imgUrl)
                    .transform(CenterCrop(), RoundedCorners(14))
                    .placeholder(android.R.drawable.ic_menu_gallery)
                    .error(R.drawable.doctor_check)
                    .into(holder.imgLicense)
            } else {
                holder.imgLicense.setImageResource(R.drawable.doctor_check)
            }

            holder.itemView.setOnClickListener { onItemClick(item) }
            holder.btnBuyShopee.setOnClickListener { onBuyClick(item) }
        }

        override fun getItemCount(): Int = items.size
    }
}
