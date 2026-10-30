from src.config import parse_port
def test_hidden_invalid():
    # already int
    assert parse_port({"port": 3000}) == 3000
