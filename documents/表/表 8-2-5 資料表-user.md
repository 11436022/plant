# 表 8-2-5 資料表-user

## 表 8-2-5 資料表-user

| 欄位名稱 | 欄位中文名稱 | 資料型態 | 資料長度 | 索引 |
| --- | --- | --- | --- | --- |
| user_id | 使用者ID | int | - | V |
| username | 使用者帳號 | varchar | 50 | V |
| password_hash | 密碼雜湊值 (Bcrypt) | varchar | 255 |  |
| email | 電子信箱 | varchar | 100 | V |
| full_name | 使用者真實姓名 | varchar | 50 |  |
| role | 角色權限 | varchar | 20 |  |
| is_email_verified | 電子信箱是否已驗證 | tinyint | 1 |  |
| email_verified_at | 信箱驗證通過時間 | datetime | - |  |
| created_at | 帳號建立時間 | datetime | - |  |
