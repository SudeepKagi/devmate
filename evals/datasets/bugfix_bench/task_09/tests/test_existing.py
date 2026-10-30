from src.config import parse_port
def test_default():
    assert parse_port({}) == 8000
