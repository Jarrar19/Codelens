from database import save_user, find_user_by_id
from utils import validate_email


def create_user(username, email):
    if not validate_email(email):
        return None

    user = {
        "username": username,
        "email": email,
    }

    return save_user(user)


def get_user(user_id):
    return find_user_by_id(user_id)


def update_user(user_id, email):
    if not validate_email(email):
        return False

    return True


def delete_user(user_id):
    return True
