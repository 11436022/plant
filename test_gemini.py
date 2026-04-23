"""相容匯出，轉接到 app.services.ai。"""

from app.services.ai import (  # noqa: F401
    classify_agriculture_term,
    client,
    diagnostic_plant,
    get_reference_lists,
    get_standard_names,
    save_to_db,
)
