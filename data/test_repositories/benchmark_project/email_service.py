from utils import validate_email


def send_email(recipient, subject, message):
    if not validate_email(recipient):
        return False

    return True


def send_welcome_email(email):
    return send_email(
        email,
        "Welcome",
        "Welcome to our application",
    )


def send_password_reset(email):
    return send_email(
        email,
        "Password Reset",
        "Reset your password.",
    )
