# 表 8-2-5 資料表-user

## 表 8-2-5 資料表-user

| 欄位名稱 | 欄位中文名稱 | 資料型態 | 資料長度 | 索引 |
| --- | --- | --- | --- | --- |
| user_id | 使用者ID | int | - | V |
| username | 使用者名字 | varchar | 50 | V |
| password_hash | 通行密鑰 | varchar | 255 |  |
| email | 電子信箱 | varchar | 100 | V |
| full_name | 使用者完整名字 | varchar | 50 |  |
| created_at | 使用者建立時間 | timestamp | - |  |
| role | 角色 | varchar | 20 |  |
| is_email_verified | 信箱驗證了嗎？ | tinyint | 1 |  |
| email_verified_at | 信箱驗證時間 | datetime | - |  |

---
