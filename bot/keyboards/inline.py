from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def earnings_menu(role: str) -> InlineKeyboardMarkup:
    buttons = []
    if role in {"seller", "admin"}:
        buttons.append([InlineKeyboardButton(text="Добавить продажу", callback_data="sale_add")])
    buttons.append([InlineKeyboardButton(text="История продаж", callback_data="sales_history_me")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def done_screenshots_button() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="Готово", callback_data="sale_done")]]
    )


def admin_panel() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Добавить участника", callback_data="admin_add_member")],
            [InlineKeyboardButton(text="Выдать предупреждение", callback_data="admin_warn_member")],
            [InlineKeyboardButton(text="Блок/Разблок", callback_data="admin_toggle_block")],
            [InlineKeyboardButton(text="Состав персонала", callback_data="admin_staff")],
            [InlineKeyboardButton(text="История продаж сотрудника", callback_data="admin_sales_history")],
        ]
    )


def role_picker(prefix: str = "role") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Intern", callback_data=f"{prefix}:intern")],
            [InlineKeyboardButton(text="Seller", callback_data=f"{prefix}:seller")],
            [InlineKeyboardButton(text="Admin", callback_data=f"{prefix}:admin")],
        ]
    )


def user_picker(action: str, users: list[dict]) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=f"{u['full_name']} ({u['role']}) | {'✅' if u['is_active'] else '⛔'}",
                callback_data=f"{action}:{u['id']}",
            )
        ]
        for u in users
    ]
    if not rows:
        rows = [[InlineKeyboardButton(text="Нет доступных пользователей", callback_data="noop")]]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def sale_decision_kb(sale_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"sale_approve:{sale_id}")],
            [InlineKeyboardButton(text="🔎 Запросить доп. проверку", callback_data=f"sale_need_more:{sale_id}")],
            [InlineKeyboardButton(text="❌ Отклонить", callback_data=f"sale_reject:{sale_id}")],
        ]
    )
