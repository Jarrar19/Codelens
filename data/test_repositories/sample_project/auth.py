from utils import generate_token


def login(username):
    token = generate_token(username)
    return token
