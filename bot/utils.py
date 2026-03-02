import secrets


def generate_one_time_password() -> str:
    return secrets.token_urlsafe(8)


def format_staff_line(user: dict) -> str:
    status = "активен" if user["is_active"] else "неактивен"
    return f"• {user['full_name'] or '-'}, @{user['username'] or '-'}, {user['role']}, {status}"
