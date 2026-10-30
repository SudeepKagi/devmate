from src.settings import get_user_setting
def test_none_profile():
    user = {"profile": None}
    assert get_user_setting(user, "theme", "light") == "light"
