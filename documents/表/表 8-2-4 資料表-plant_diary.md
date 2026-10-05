# 表 8-2-4 資料表-plant_diary

## 表 8-2-4 資料表-plant_diary

| 欄位名稱 | 欄位中文名稱 | 資料型態 | 資料長度 | 索引 |
| --- | --- | --- | --- | --- |
| id | 日誌ID | int | - | V |
| user_id | 使用者ID | int | - | V |
| crop_id | 農作物ID | int | - | V |
| status_name | 診斷病害名稱 | varchar | 100 |  |
| image_url | 診斷影像路徑 | varchar | 2048 |  |
| disease_id | 疾病ID | int | - | V |
| pest_id | 害蟲ID | int | - | V |
| confidence | AI信心度 | float | - |  |
| category | 異常分類 | varchar | 20 |  |
| requires_review | 是否需人工覆核 | tinyint | 1 |  |
| grounding_source | 診斷佐證技術來源 | varchar | 64 |  |
| reference_source | 參考資料來源單位 | varchar | 100 |  |
| reference_url | 參考資料來源網址 | varchar | 2048 |  |
| reference_record_id | 官方來源紀錄編號 | varchar | 128 |  |
| suggestion | AI診斷建議說明 | text | - |  |
| treatment | 防治措施處方 | text | - |  |
| user_note | 使用者個人備忘筆記 | text | - |  |
| user_corrected_status | 使用者糾錯狀態 | varchar | 100 |  |
| created_at | 診斷建立時間 | datetime | - |  |
