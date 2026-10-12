from database import find_user_by_id
from utils import generate_transaction_id


def process_payment(user_id, amount):
    user = find_user_by_id(user_id)

    if not user:
        return None

    transaction_id = generate_transaction_id()

    return {
        "transaction_id": transaction_id,
        "amount": amount,
    }


def refund_payment(transaction_id):
    return {
        "transaction_id": transaction_id,
        "status": "refunded",
    }


def verify_payment(transaction_id):
    return transaction_id is not None


def calculate_total(amount, tax):
    return amount + tax
