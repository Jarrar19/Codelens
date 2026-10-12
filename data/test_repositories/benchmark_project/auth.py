from database import find_user
from utils import generate_token, hash_password


def login_user(username, password):
    password_hash = hash_password(password)
    user = find_user(username, password_hash)

    if user:
        return generate_token(user["id"])

    return None


def logout_user(user_id):
    return invalidate_token(user_id)


def invalidate_token(user_id):
    return f"invalidated-{user_id}"


def verify_token(token):
    return token.startswith("TOKEN-")


def refresh_token(user_id):
    return generate_token(user_id)
