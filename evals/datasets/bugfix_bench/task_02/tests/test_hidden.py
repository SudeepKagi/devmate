from src.roles import RoleManager
def test_hidden_multiple():
    m1 = RoleManager()
    m2 = RoleManager()
    m1.add_role("viewer")
    assert "viewer" not in m2.roles
    assert len(m2.roles) == 0
