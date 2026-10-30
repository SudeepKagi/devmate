from src.config import parse_port
def test_port_is_integer():
    p = parse_port({"port": "9000"})
    assert isinstance(p, int), f"Expected int, got {type(p)}"
    assert p == 9000
