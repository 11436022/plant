# 表 8-2-8 資料表-diagnosis_feedback

## 表 8-2-8 資料表-diagnosis_feedback

| 欄位名稱 | 欄位中文名稱 | 資料型態 | 資料長度 | 索引 |
| --- | --- | --- | --- | --- |
| id | 反饋ID | int | - | V |
| prediction_id | 關聯診斷序號 | varchar | 64 | V |
| user_id | 使用者ID (可匿名) | int | - | V |
| image_url | 反饋圖片路徑 | varchar | 255 |  |
| original_plant_name | AI初判作物名 | varchar | 100 |  |
| original_disease_name | AI初判病害名 | varchar | 100 |  |
| is_plant_error | 作物初判是否錯誤 | tinyint | 1 |  |
| is_disease_error | 病害初判是否錯誤 | tinyint | 1 |  |
| corrected_plant_name | 使用者修正作物名 | varchar | 100 |  |
| corrected_disease_name | 使用者修正病害名 | varchar | 100 |  |
| created_at | 反饋提報建立時間 | datetime | - |  |
