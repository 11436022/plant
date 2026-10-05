# 表 8-2-2 資料表-disease

## 表 8-2-2 資料表-disease

| 欄位名稱 | 欄位中文名稱 | 資料型態 | 資料長度 | 索引 |
| --- | --- | --- | --- | --- |
| disease_id | 疾病ID | int | - | V |
| crop_id | 農作物ID | int | - | V |
| disease_name | 疾病中文名 | varchar | 100 |  |
| description | 病徵病理描述 | text | - |  |
| treatment | 防治建議處方 | text | - |  |
| source_name | 資料來源單位 | varchar | 100 |  |
| source_url | 官方來源網址 | varchar | 2048 |  |
| source_record_id | 官方來源紀錄編號 | varchar | 128 |  |
