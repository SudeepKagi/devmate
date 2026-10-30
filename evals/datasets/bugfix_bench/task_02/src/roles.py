class RoleManager:
    def __init__(self, initial_roles=[]):  # BUG: mutable default
        self.roles = initial_roles

    def add_role(self, role):
        self.roles.append(role)
        return self.roles
