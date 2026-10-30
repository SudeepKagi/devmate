def get_user_setting(user, setting_name, default=None):
    profile = user.get("profile")
    # BUG: profile can be None
    return profile.get("settings", {}).get(setting_name, default)
