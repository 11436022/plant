# 表 8-2-4 資料表-plant_diary

## 表 8-2-4 資料表-plant_diary

| 欄位名稱 | 欄位中文名稱 | 資料型態 | 資料長度 | 索引 |
| --- | --- | --- | --- | --- |
| id | 日誌ID | int | - | V |
| user_id | 使用者ID | int | - |  |
| crop_id | 農作物ID | int | - |  |
| status_name | 疾病形容 | varchar | 100 |  |
| image_url | 解決方法 | varchar | 2048 |  |
| disease_id | 疾病ID | int | - |  |
| pest_id | 害蟲ID | int | - |  |
| confidence | 信心度 | float | - |  |
| suggestion | 形容 | text | - |  |
| treatment | 解決方法 | text | - |  |
| user_note | 使用者筆記 | text | - |  |
| created_at | 日誌時間 | timestamp | - |  |

---
