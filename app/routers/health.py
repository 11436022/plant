from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/")
def read_root():
    """基本健康檢查。"""

    return {"message": "Plant API is running. Open /docs for the API docs."}
