from src.roles import RoleManager
def test_instance_isolation():
    mgr1 = RoleManager()
    mgr1.add_role("editor")
    mgr2 = RoleManager()
    assert mgr2.roles == [], f"Expected empty roles, got {mgr2.roles}"
