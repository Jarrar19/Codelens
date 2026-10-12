import hashlib
import uuid
import re


def hash_password(password):
    return hashlib.sha256(
        password.encode()
    ).hexdigest()


def generate_token(user_id):
    return f"TOKEN-{user_id}"


def generate_transaction_id():
    return str(uuid.uuid4())


def validate_email(email):
    pattern = r"^[^@]+@[^@]+\.[^@]+$"
    return re.match(pattern, email) is not None


def normalize_username(username):
    return username.strip().lower()


def format_currency(amount):
    return f"${amount:.2f}"
