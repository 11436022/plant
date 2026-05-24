import pytest

# 同樣，為了讓測試檔案能找到 app 模組
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent
sys.path.append(str(ROOT_DIR))

# 從 auth 路由中匯入我們用來處理密碼的 pwd_context
from app.routers.auth import pwd_context


def test_password_hashing_and_verification():
    """
    測試密碼雜湊與驗證流程是否正常。
    確保一個密碼被雜湊後，可以被成功驗證，而錯誤的密碼則會驗證失敗。
    """
    # 1. 準備 (Arrange)
    password = "my_secure_password_for_testing"
    wrong_password = "wrong_password"

    # 2. 執行 (Act)
    # 雜湊原始密碼
    hashed_password = pwd_context.hash(password)

    # 3. 斷言 (Assert)
    # 斷言雜湊後的密碼不是原始密碼
    assert hashed_password != password

    # 斷言使用原始密碼進行驗證，結果應該為 True
    assert pwd_context.verify(password, hashed_password) is True

    # 斷言使用錯誤的密碼進行驗證，結果應該為 False
    assert pwd_context.verify(wrong_password, hashed_password) is False