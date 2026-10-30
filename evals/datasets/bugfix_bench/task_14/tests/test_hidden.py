from src.cloner import create_config
def test_hidden_independent():
    c1 = create_config({"auth": False})
    c2 = create_config()
    assert c2["features"]["auth"] is True
