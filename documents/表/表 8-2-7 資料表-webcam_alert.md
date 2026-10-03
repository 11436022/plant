# 表 8-2-7 資料表-webcam_alert

## 表 8-2-7 資料表-webcam_alert

| 欄位名稱 | 欄位中文名稱 | 資料型態 | 資料長度 | 索引 |
| --- | --- | --- | --- | --- |
| id | 警報ID | bigint | - | V |
| user_id | 使用者ID | int | - | V |
| crop_id | 農作物ID | int | - | V |
| category | 異常類別 | varchar | 20 |  |
| status_name | 病害或蟲害名稱 | varchar | 100 |  |
| confidence | 信心度 | float | - |  |
| consecutive_matches | 連續一致次數 | int | - |  |
| image_url | 警報影像位置 | varchar | 2048 |  |
| email_sent | Email是否寄送 | tinyint | 1 |  |
| acknowledged_at | 確認時間 | datetime | - |  |
| created_at | 警報建立時間 | datetime | - |  |

---
