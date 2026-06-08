import shutil
import traceback # <--- 導入 traceback 模組
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import crud
from app.db import models
from app.db.session import get_db
from app.schemas.feedback import DiagnosisFeedbackCreate, DiagnosisFeedbackResponse
from app.services.auth import get_current_user
# 核心修改：引入處理檔案和快取所需的工具
from app.services.files import create_feedback_image_path
from app.routers.prediction import prediction_cache


router = APIRouter(
    tags=["feedback"]
)

@router.post("/diagnosis", response_model=DiagnosisFeedbackResponse)
def create_diagnosis_feedback(
    feedback_data: DiagnosisFeedbackCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    接收、處理並儲存使用者的診斷回饋，包含圖片轉存。
    """
    # 1. 從快取中查找預測結果
    cached_data = prediction_cache.get(feedback_data.prediction_id)
    if not cached_data:
        raise HTTPException(status_code=404, detail="Prediction ID not found or has expired.")

    temp_path = Path(cached_data["temp_path"])
    if not temp_path.exists():
        raise HTTPException(status_code=404, detail="Temporary image file not found. It might have been cleaned up.")

    # 2. 將圖片從臨時資料夾移動到正式的 feedback_uploads 資料夾
    formal_path = create_feedback_image_path(temp_path.name)
    try:
        shutil.move(str(temp_path), formal_path)

        # 3. 計算並設定正確的、用於儲存到資料庫的相對路徑
        relative_path = formal_path.relative_to(Path.cwd())
        feedback_data.image_url = relative_path.as_posix()

        # 4. 呼叫 CRUD 操作，將包含正確圖片路徑的資料存入資料庫
        db_feedback = crud.create_diagnosis_feedback(
            db=db, feedback_data=feedback_data, user_id=current_user.user_id
        )
        
        # 5. 清除已處理完畢的快取
        del prediction_cache[feedback_data.prediction_id]

        return db_feedback

    except Exception as e:
        # 如果過程中發生任何錯誤，復原檔案移動並回滾資料庫
        if formal_path.exists() and not temp_path.exists():
            shutil.move(str(formal_path), temp_path)
        db.rollback()

        # 關鍵修改：強制在後端終端機印出完整的錯誤報告
        print("="*80)
        print("💥 AN ERROR OCCURRED IN create_diagnosis_feedback 💥")
        traceback.print_exc()
        print("="*80)

        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred during feedback creation: {str(e)}"
        )