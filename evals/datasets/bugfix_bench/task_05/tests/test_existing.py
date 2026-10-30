from src.headers import get_auth_token
def test_valid_bearer():
    assert get_auth_token({"Authorization": "Bearer secret123"}) == "secret123"
