from datetime import datetime, timezone, timedelta
from typing import Any, Optional

TAIWAN_TZ = timezone(timedelta(hours=8))

def format_taiwan_time(dt: Any, fmt: str = "%Y-%m-%d %H:%M") -> str:
    """將 UTC 或資料庫時間轉換為台灣時間 (UTC+8) 格式字串。"""
    if not dt:
        return ""
    if isinstance(dt, str):
        try:
            dt_clean = dt.strip().replace("Z", "+00:00")
            if " " in dt_clean and "T" not in dt_clean:
                dt_clean = dt_clean.replace(" ", "T")
            if "+" not in dt_clean and not dt_clean.endswith("+00:00"):
                dt_clean += "+00:00"
            dt = datetime.fromisoformat(dt_clean)
        except Exception:
            return str(dt)
    if isinstance(dt, datetime):
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(TAIWAN_TZ).strftime(fmt)
    return str(dt)
