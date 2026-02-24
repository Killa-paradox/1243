import secrets


def generate_one_time_password() -> str:
    return secrets.token_urlsafe(8)


def format_staff_line(user: dict, month_sales: float) -> str:
    status = "Активен" if user["is_active"] else "Заблокирован"
    return (
        f"• {user['full_name']} (@{user['username'] or '-'})\n"
        f"  Роль: {user['role']} | Статус: {status}\n"
        f"  Предупреждения: {user['warnings']} | Продажи за месяц: {month_sales:.2f}"
    )
