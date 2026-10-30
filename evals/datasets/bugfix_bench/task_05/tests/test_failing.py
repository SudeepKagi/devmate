from src.headers import get_auth_token
def test_missing_auth():
    assert get_auth_token({}) is None
