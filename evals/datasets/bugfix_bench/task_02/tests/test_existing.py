from src.roles import RoleManager
def test_explicit_roles():
    mgr = RoleManager(["admin"])
    assert mgr.roles == ["admin"]
