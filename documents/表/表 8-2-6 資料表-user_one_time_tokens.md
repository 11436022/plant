# 表 8-2-6 資料表-user_one_time_tokens

## 表 8-2-6 資料表-user_one_time_tokens

| 欄位名稱 | 欄位中文名稱 | 資料型態 | 資料長度 | 索引 |
| --- | --- | --- | --- | --- |
| id | 權杖ID | bigint | - | V |
| user_id | 使用者ID | int | - | V |
| purpose | 權杖用途類型 | varchar | 32 | V |
| token_hash | 權杖雜湊值 (SHA-256) | varchar | 64 | V |
| expires_at | 權杖到期時間 | datetime | - |  |
| used_at | 權杖使用兌換時間 | datetime | - |  |
| created_at | 權杖建立時間 | datetime | - |  |
