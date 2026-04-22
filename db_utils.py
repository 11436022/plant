"""相容匯出，轉接到 app.db.session 與 app.services.knowledge。"""

from app.db.session import get_db_connection  # noqa: F401
from app.services.knowledge import get_crop_id_by_name, get_or_complete_knowledge  # noqa: F401
