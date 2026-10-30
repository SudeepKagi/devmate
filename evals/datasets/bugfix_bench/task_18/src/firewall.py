BLACKLIST = {"192.168.1.100", "10.0.0.5"}

def is_ip_allowed(ip):
    # BUG: reversed condition
    if ip in BLACKLIST:
        return True
    return False
