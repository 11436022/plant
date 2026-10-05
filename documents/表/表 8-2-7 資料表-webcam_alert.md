# 表 8-2-7 資料表-webcam_alert

## 表 8-2-7 資料表-webcam_alert

| 欄位名稱 | 欄位中文名稱 | 資料型態 | 資料長度 | 索引 |
| --- | --- | --- | --- | --- |
| id | 警報ID | bigint | - | V |
| user_id | 使用者ID | int | - | V |
| crop_id | 農作物ID | int | - | V |
| category | 異常分類 | varchar | 20 |  |
| status_name | 警報病蟲害名稱 | varchar | 100 |  |
| confidence | 辨識信心度 | float | - |  |
| requires_review | 是否需人工覆核 | tinyint | 1 |  |
| grounding_source | 診斷佐證技術來源 | varchar | 64 |  |
| reference_source | 參考資料來源單位 | varchar | 100 |  |
| reference_url | 參考資料來源網址 | varchar | 2048 |  |
| reference_record_id | 官方來源紀錄編號 | varchar | 128 |  |
| session_id | 監控串流會話ID | varchar | 64 | V |
| region_id | 監控檢驗區域編號 | varchar | 64 |  |
| consecutive_matches | 連續共識命中次數 | int | - |  |
| image_url | 警報影格影像路徑 | varchar | 2048 |  |
| email_sent | 是否已寄發緊急郵件 | tinyint | 1 |  |
| acknowledged_at | 使用者確認已讀時間 | datetime | - |  |
| created_at | 警報觸發建立時間 | datetime | - |  |
