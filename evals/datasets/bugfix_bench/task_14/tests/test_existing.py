from src.cloner import create_config
def test_base_config():
    c = create_config()
    assert c["version"] == "1.0"
