from src.uuid_validator import is_valid_uuid
def test_invalid_prefix():
    assert is_valid_uuid("prefix-12345678-1234-1234-1234-123456789abc-suffix") is False
