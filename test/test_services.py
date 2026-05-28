import hashlib
import pytest

# 為了讓測試檔案能找到 app 模組，我們需要一些路徑魔法
import sys
from pathlib import Path

# 將專案根目錄加到 Python 的搜尋路徑中
ROOT_DIR = Path(__file__).parent.parent
sys.path.append(str(ROOT_DIR))

# 現在我們可以從 app 中匯入我們想測試的函數了
from app.services.account_recovery import _hash_token


def test_hash_token_produces_valid_sha256_hash():
    """
    測試 _hash_token 函數是否能產生一個有效的 SHA-256 雜湊值。
    """
    # 1. 準備 (Arrange)
    raw_token = "my_super_secret_test_token_123"

    # 2. 執行 (Act)
    hashed_token = _hash_token(raw_token)

    # 3. 斷言 (Assert)
    # 斷言雜湊後的結果不是原始 token
    assert hashed_token != raw_token

    # 斷言雜湊後的結果是一個 64 個字元的十六進位字串 (SHA-256 的特性)
    assert isinstance(hashed_token, str)
    assert len(hashed_token) == 64

    # 斷言結果與我們手動計算的結果一致，確保演算法是正確的
    expected_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    assert hashed_token == expected_hash