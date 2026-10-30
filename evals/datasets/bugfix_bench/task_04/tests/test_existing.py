from src.settings import get_user_setting
def test_valid_profile():
    user = {"profile": {"settings": {"theme": "dark"}}}
    assert get_user_setting(user, "theme") == "dark"
