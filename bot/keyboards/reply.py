from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

MENU_STAFF = "👥 Персонал"
MENU_EARNINGS = "💰 Заработок"
MENU_PROFILE = "🙍 Профиль"
MENU_STATS = "📊 Статистика"
MENU_INFO = "ℹ️ Инфо"
MENU_ADMIN = "🛠 Админ-панель"


def main_menu(role: str) -> ReplyKeyboardMarkup:
    common = [
        [KeyboardButton(text=MENU_STAFF)],
        [KeyboardButton(text=MENU_PROFILE), KeyboardButton(text=MENU_STATS)],
        [KeyboardButton(text=MENU_INFO)],
    ]

    if role in {"seller", "admin"}:
        common.insert(1, [KeyboardButton(text=MENU_EARNINGS)])

    if role == "admin":
        common.append([KeyboardButton(text=MENU_ADMIN)])

    return ReplyKeyboardMarkup(keyboard=common, resize_keyboard=True)
