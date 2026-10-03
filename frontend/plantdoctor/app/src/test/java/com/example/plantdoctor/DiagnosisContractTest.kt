package com.example.plantdoctor

import com.google.gson.Gson
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.toRequestBody
import okio.Buffer
import org.junit.Assert.*
import org.junit.Test
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import java.util.Locale
import java.util.UUID

class DiagnosisContractTest {
    private val gson = Gson()
    private val diagnosisJson = """
        {
          "crop_name": "Tomato", "status_name": "Original diagnosis",
          "confidence": 0.91, "category": "disease",
          "suggestion": "Original advice", "treatment": "Original treatment",
          "requires_review": true, "grounding_source": "database",
          "reference_source": "Reference dataset",
          "reference_url": "https://example.org/record",
          "reference_record_id": "00042"
        }
    """.trimIndent()

    @Test
    fun predictionMetadataSurvivesActivityJsonRoundTrip() {
        val response = gson.fromJson(
            """{"prediction_id":"prediction-1","analysis_result":$diagnosisJson}""",
            PredictionResponse::class.java
        )
        val result = gson.fromJson(gson.toJson(response.analysis_result), AnalysisResult::class.java)
        assertEquals(0.91, result.confidence!!, 0.0001)
        assertEquals("disease", result.category)
        assertEquals(true, result.requires_review)
        assertEquals("database", result.grounding_source)
        assertEquals("Reference dataset", result.reference_source)
        assertEquals("https://example.org/record", result.reference_url)
        assertEquals("00042", result.reference_record_id)
    }

    @Test
    fun diaryMetadataDoesNotReplaceOriginalWithCorrection() {
        val json = diagnosisJson.dropLast(1) + """,
            "id": 7, "created_at": "2026-10-03T00:00:00",
            "image_url": "/static/image.jpg", "user_note": null,
            "user_corrected_status": "User observation"
        }"""
        val item = gson.fromJson(json, HistoryItem::class.java)
        val confirmed = gson.fromJson(json, DiaryConfirmData::class.java)
        assertEquals("Original diagnosis", item.status_name)
        assertEquals("User observation", item.user_corrected_status)
        assertEquals("Original advice", item.suggestion)
        assertEquals("Original treatment", item.treatment)
        assertEquals(0.91, item.confidence!!, 0.0001)
        assertEquals("disease", item.category)
        assertEquals(true, item.requires_review)
        assertEquals("database", item.grounding_source)
        assertEquals("Reference dataset", item.reference_source)
        assertEquals("https://example.org/record", item.reference_url)
        assertEquals("00042", item.reference_record_id)
        assertEquals(item.confidence, confirmed.confidence)
        assertEquals(item.category, confirmed.category)
        assertEquals(item.requires_review, confirmed.requires_review)
        assertEquals(item.grounding_source, confirmed.grounding_source)
        assertEquals(item.reference_source, confirmed.reference_source)
        assertEquals(item.reference_url, confirmed.reference_url)
        assertEquals(item.reference_record_id, confirmed.reference_record_id)
    }

    @Test
    fun omittedLegacyMetadataRemainsUnknown() {
        val analysis = gson.fromJson("""{"crop_name":"Tomato"}""", AnalysisResult::class.java)
        val history = gson.fromJson("""{"id":1}""", HistoryItem::class.java)
        assertNull(analysis.requires_review)
        assertNull(analysis.reference_url)
        assertNull(history.confidence)
        assertNull(history.requires_review)
        val summary = formatDiagnosisMetadata(null, null, null, null, null, null, null)
        assertTrue(summary.contains("未提供複核狀態"))
        assertFalse(summary.contains("系統未標記"))
    }

    @Test
    fun confidenceFormattingIsFiniteAndDoesNotClaimExpertReview() {
        for (invalid in listOf(Double.NaN, Double.POSITIVE_INFINITY, -0.1, 1.1)) {
            val summary = formatDiagnosisMetadata(invalid, null, true, null, null, null, null)
            assertTrue(summary.contains("模型信心值：未提供"))
            assertTrue(summary.contains("需要人工複核"))
        }
        val summary = formatDiagnosisMetadata(0.91, "disease", false, "database", "source", "url", "id")
        assertTrue(summary.contains(String.format(Locale.getDefault(), "%.1f%%", 91.0)))
        assertTrue(summary.contains("非準確率"))
        assertTrue(summary.contains("不代表已由專家審核"))
    }

    @Test
    fun registrationDistinguishesFalseFromMissingEmailStatus() {
        val sent = gson.fromJson("""{"status":"success","email_sent":true}""", GenericResponse::class.java)
        val failed = gson.fromJson("""{"status":"success","email_sent":false}""", GenericResponse::class.java)
        val legacy = gson.fromJson("""{"status":"success"}""", GenericResponse::class.java)
        assertEquals(true, sent.email_sent)
        assertEquals(false, failed.email_sent)
        assertNull(legacy.email_sent)
    }

    @Test
    fun multipartAcceptsLegacyAndScopedCallsitesWithoutNetwork() {
        val api = Retrofit.Builder()
            .baseUrl("http://localhost/api/v1/")
            .addConverterFactory(GsonConverterFactory.create())
            .build()
            .create(PlantApiService::class.java)
        val file = MultipartBody.Part.createFormData(
            "file", "frame.jpg", byteArrayOf(1, 2, 3).toRequestBody("image/jpeg".toMediaTypeOrNull())
        )
        val legacy = Buffer().also { api.analyzeWebcamFrame(file).request().body!!.writeTo(it) }.readUtf8()
        assertTrue(legacy.contains("name=\"file\""))
        assertFalse(legacy.contains("name=\"session_id\""))
        assertFalse(legacy.contains("name=\"region_id\""))
        val sessionId = UUID.randomUUID().toString()
        val regionId = UUID.randomUUID().toString()
        val textType = "text/plain".toMediaTypeOrNull()
        val scoped = Buffer().also {
            api.analyzeWebcamFrame(
                file, sessionId.toRequestBody(textType), regionId.toRequestBody(textType)
            ).request().body!!.writeTo(it)
        }.readUtf8()
        assertTrue(sessionId.length <= 64 && regionId.length <= 64)
        assertTrue(scoped.contains("name=\"session_id\""))
        assertTrue(scoped.contains("name=\"region_id\""))
        assertTrue(scoped.contains(sessionId))
        assertTrue(scoped.contains(regionId))
    }

    @Test
    fun alertScopeAndEmailStatusArePreserved() {
        val json = """{"id":8,"session_id":"run-1","region_id":"region-2","email_sent":false}"""
        val alert = gson.fromJson(json, WebcamAlertItem::class.java)
        assertEquals("run-1", alert.session_id)
        assertEquals("region-2", alert.region_id)
        assertEquals(false, alert.email_sent)
        val legacy = gson.fromJson("""{"id":8}""", WebcamAlertItem::class.java)
        assertNull(legacy.session_id)
        assertNull(legacy.region_id)
    }

    @Test
    fun monitoringReasonAndLegacyStatusDecodeFromFullResponses() {
        for (key in listOf("reason", "status")) {
            val json = """
                {
                  "status": "success",
                  "diagnosis": $diagnosisJson,
                  "monitoring": {
                    "streak": 2, "triggered": false,
                    "$key": "collecting_consensus", "required_matches": 3,
                    "session_id": "run-1", "region_id": "region-2"
                  },
                  "alert": null
                }
            """.trimIndent()
            val response = gson.fromJson(json, WebcamAnalyzeResponse::class.java)
            assertEquals("success", response.status)
            assertEquals("collecting_consensus", response.monitoring.status)
            assertEquals(3, response.monitoring.required_matches)
            assertEquals("run-1", response.monitoring.session_id)
            assertEquals("region-2", response.monitoring.region_id)
            assertTrue(response.monitoring.matchesScope("run-1", "region-2"))
            val encoded = gson.toJsonTree(response.monitoring).asJsonObject
            assertTrue(encoded.has("reason"))
            assertFalse(encoded.has("status"))
        }
    }

    @Test
    fun missingNullAndUnknownMonitoringReasonsHaveReadableFallbacks() {
        val fixtures = listOf(
            """{"streak":0,"triggered":false}""",
            """{"streak":0,"triggered":false,"reason":null}""",
            """{"streak":0,"triggered":false,"reason":""}""",
            """{"streak":0,"triggered":false,"reason":"   "}""",
            """{"streak":0,"triggered":false,"status":null}"""
        )
        for (json in fixtures) {
            val state = gson.fromJson(json, WebcamMonitoringState::class.java)
            assertEquals("未提供監控狀態", state.statusLabel())
        }
        val unknown = gson.fromJson(
            """{"streak":0,"triggered":false,"reason":"future_reason"}""",
            WebcamMonitoringState::class.java
        )
        assertEquals("無法辨識監控狀態", unknown.statusLabel())
        assertFalse(unknown.statusLabel().contains("future_reason"))
    }

    @Test
    fun knownMonitoringReasonsUseTraditionalChineseLabels() {
        val labels = mapOf(
            "triggered" to "已建立警報",
            "cooldown" to "警報冷卻中",
            "collecting_consensus" to "正在累積連續判定",
            "not_a_grounded_anomaly" to "未符合警報條件"
        )
        for ((reason, expectedLabel) in labels) {
            val state = WebcamMonitoringState(0, false, status = reason)
            assertEquals(expectedLabel, state.statusLabel())
        }
    }

    @Test
    fun monitoringScopeRejectsContradictoryEchoesButAcceptsLegacyOmission() {
        val state = WebcamMonitoringState(
            2, false, session_id = "run-1", region_id = "region-2"
        )
        assertTrue(state.matchesScope("run-1", "region-2"))
        assertFalse(state.matchesScope("old-run", "region-2"))
        assertFalse(state.matchesScope("run-1", "different-region"))
        assertFalse(state.copy(session_id = "").matchesScope("run-1", "region-2"))
        assertFalse(state.copy(region_id = "").matchesScope("run-1", "region-2"))
        assertTrue(state.copy(session_id = null).matchesScope("run-1", "region-2"))
        assertTrue(state.copy(region_id = null).matchesScope("run-1", "region-2"))
        val legacy = gson.fromJson(
            """{"streak":0,"triggered":false}""",
            WebcamMonitoringState::class.java
        )
        assertTrue(legacy.matchesScope("run-1", "region-2"))
    }
}
