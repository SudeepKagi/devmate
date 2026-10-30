from src.firewall import is_ip_allowed
def test_blocked_ip():
    assert is_ip_allowed("192.168.1.100") is False
