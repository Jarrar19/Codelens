from database import find_user_by_id


def generate_report(user_id):
    user = find_user_by_id(user_id)

    if not user:
        return None

    return {
        "user": user,
        "status": "generated",
    }


def export_report(report):
    return str(report)


def calculate_report_total(values):
    return sum(values)


def summarize_report(report):
    return {
        "keys": len(report)
    }
