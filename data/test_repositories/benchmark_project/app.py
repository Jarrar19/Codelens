from auth import login_user, logout_user
from users import create_user, get_user
from payments import process_payment
from reports import generate_report


def start_application():
    print("Application started")


def handle_login(username, password):
    return login_user(username, password)


def handle_logout(user_id):
    return logout_user(user_id)


def register_user(username, email):
    return create_user(username, email)


def show_user(user_id):
    return get_user(user_id)


def make_payment(user_id, amount):
    return process_payment(user_id, amount)


def create_report(user_id):
    return generate_report(user_id)


def main():
    start_application()


if __name__ == "__main__":
    main()
