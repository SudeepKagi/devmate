from src.uuid_validator import is_valid_uuid
def test_valid():
    assert is_valid_uuid("12345678-1234-1234-1234-123456789abc") is True
