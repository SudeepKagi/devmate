from src.uuid_validator import is_valid_uuid
def test_hidden_short():
    assert is_valid_uuid("1234") is False
    assert is_valid_uuid("") is False
