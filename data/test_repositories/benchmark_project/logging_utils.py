def log_info(message):
    print(f"INFO: {message}")


def log_error(message):
    print(f"ERROR: {message}")


def log_warning(message):
    print(f"WARNING: {message}")


def audit_action(user_id, action):
    print(f"AUDIT: {user_id} -> {action}")
