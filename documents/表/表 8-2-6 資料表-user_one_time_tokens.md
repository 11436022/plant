# 表 8-2-6 資料表-user_one_time_tokens

## 表 8-2-6 資料表-user_one_time_tokens

| 欄位名稱 | 欄位中文名稱 | 資料型態 | 資料長度 | 索引 |
| --- | --- | --- | --- | --- |
| id | 編號 | bigint | - | V |
| user_id | 使用者ID | int | - | V |
| purpose | 目的 | int | 32 | V |
| token_hash | 通行密鑰 | char | 64 | V |
| expires_at | 到期時間 | datetime | - |  |
| used_at | 使用時間 | datetime | - |  |
| created_at | 創立時間 | datetime | - |  |

---
