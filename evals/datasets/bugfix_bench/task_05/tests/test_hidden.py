from src.headers import get_auth_token
def test_hidden_case_insensitive():
    # If case sensitivity or plain token
    assert get_auth_token({"Authorization": "token_abc"}) == "token_abc"
def test_hidden_none_headers():
    assert get_auth_token({"Content-Type": "application/json"}) is None
