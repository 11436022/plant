# 表 8-2-8 資料表-diagnosis_feedback

## 表 8-2-8 資料表-diagnosis_feedback

| 欄位名稱 | 欄位中文名稱 | 欄位中文名稱 | 資料型態 | 資料型態 | 資料長度 | 資料長度 | 索引 | 索引 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| id | 反饋ID | int | int | - | - | V | V |  |
| prediction_id | 關聯預測ID | varchar | varchar | 64 | 64 | V | V |  |
| user_id | 使用者ID | int | int | - | - |  |  |  |
| image_url | 反饋圖片路徑 | varchar | varchar | 255 | 255 |  |  |  |
| original_plant_name | AI初判植物名 | varchar | varchar | 100 | 100 |  |  |  |
| original_disease_name | AI初判病害名 | varchar | varchar | 100 | 100 |  |  |  |
| is_plant_error | 植物名是否錯誤 | tinyint | tinyint | 1 | 1 |  |  |  |
| is_disease_error | 病害名是否錯誤 | tinyint | tinyint | 1 | 1 |  |  |  |
| corrected_plant_name | 修正後植物名 | varchar | varchar | 100 | 100 |  |  |  |
| corrected_disease_name | 修正後病害名 | varchar | varchar | 100 | 100 |  |  |  |
| created_at | 反饋建立時間 | datetime | datetime | - | - |  |  |  |

---
