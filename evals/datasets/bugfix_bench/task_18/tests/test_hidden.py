from src.firewall import is_ip_allowed
def test_hidden_allowed():
    assert is_ip_allowed("8.8.8.8") is True
def test_hidden_second_blacklist():
    assert is_ip_allowed("10.0.0.5") is False
