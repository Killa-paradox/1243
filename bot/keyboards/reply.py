from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


def main_menu(role: str) -> ReplyKeyboardMarkup:
    common = [
        [KeyboardButton(text="Информация обо всём персонале")],
        [KeyboardButton(text="Профиль"), KeyboardButton(text="Статистика")],
        [KeyboardButton(text="Инфо")],
    ]

    if role in {"seller", "admin"}:
        common.insert(1, [KeyboardButton(text="Заработок за месяц")])

    if role == "admin":
        common.append([KeyboardButton(text="Админ-панель")])

    return ReplyKeyboardMarkup(keyboard=common, resize_keyboard=True)
