"""相容入口，實際應用位於 app.main。"""

from app.core.config import API_HOST, API_PORT
from app.main import app


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=API_HOST, port=API_PORT)
