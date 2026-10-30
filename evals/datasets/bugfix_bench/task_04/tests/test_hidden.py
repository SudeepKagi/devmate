from src.settings import get_user_setting
def test_hidden_missing_profile_key():
    assert get_user_setting({}, "theme", "blue") == "blue"
def test_hidden_empty_settings():
    assert get_user_setting({"profile": {"settings": None}}, "k", "def") == "def"
