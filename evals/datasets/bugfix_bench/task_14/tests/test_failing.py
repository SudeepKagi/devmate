from src.cloner import create_config, BASE_TEMPLATE
def test_isolated_templates():
    c1 = create_config({"auth": False})
    assert BASE_TEMPLATE["features"]["auth"] is True, "BASE_TEMPLATE was corrupted!"
