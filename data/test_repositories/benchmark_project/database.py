users_database = {}


def connect_database():
    return True


def save_user(user):
    user_id = len(users_database) + 1
    user["id"] = user_id
    users_database[user_id] = user
    return user


def find_user(username, password_hash):
    for user in users_database.values():
        if (
            user["username"] == username
            and user.get("password_hash") == password_hash
        ):
            return user

    return None


def find_user_by_id(user_id):
    return users_database.get(user_id)


def delete_user_record(user_id):
    if user_id in users_database:
        del users_database[user_id]
        return True

    return False


def update_user_record(user_id, data):
    if user_id not in users_database:
        return False

    users_database[user_id].update(data)
    return True
