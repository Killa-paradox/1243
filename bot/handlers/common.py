from aiogram import F, Router
from aiogram.types import Message

from ..db import Database
from ..keyboards.inline import earnings_menu
from ..utils import format_staff_line

router = Router()


async def ensure_auth(message: Message, db_user: dict | None) -> bool:
    if not db_user:
        await message.answer("Сначала выполните /start и авторизуйтесь одноразовым паролем.")
        return False
    return True


@router.message(F.text == "Информация обо всём персонале")
async def staff_info(message: Message, db: Database, db_user: dict | None = None) -> None:
    if not await ensure_auth(message, db_user):
        return

    staff = await db.all_staff()
    if not staff:
        await message.answer("Нет зарегистрированных сотрудников.")
        return

    lines = ["Состав персонала:"]
    for member in staff:
        sales = await db.month_sales(member["id"])
        lines.append(format_staff_line(member, sales))
    await message.answer("\n\n".join(lines))


@router.message(F.text == "Профиль")
async def profile(message: Message, db: Database, db_user: dict | None = None) -> None:
    if not await ensure_auth(message, db_user):
        return

    month_sum = await db.month_sales(db_user["id"])
    status = "Активен" if db_user["is_active"] else "Заблокирован"
    await message.answer(
        "\n".join(
            [
                f"Имя: {db_user['full_name']}",
                f"Username: @{db_user['username'] or '-'}",
                f"Роль: {db_user['role']}",
                f"Продажи за месяц: {month_sum:.2f}",
                f"Предупреждения: {db_user['warnings']}",
                f"Статус: {status}",
            ]
        )
    )


@router.message(F.text == "Статистика")
async def stats(message: Message, db: Database, db_user: dict | None = None) -> None:
    if not await ensure_auth(message, db_user):
        return

    amount, count = await db.month_stats(db_user["id"])
    await message.answer(f"Статистика за месяц:\nСумма: {amount:.2f}\nКоличество подтверждённых продаж: {count}")


@router.message(F.text == "Инфо")
async def info(message: Message, db_user: dict | None = None) -> None:
    if not await ensure_auth(message, db_user):
        return
    await message.answer(
        "ALTShop Bot\n"
        "Правила: работайте честно, прикладывайте подтверждения продаж.\n"
        "Контакты: @altshop_admin"
    )


@router.message(F.text == "Заработок за месяц")
async def month_earnings(message: Message, db: Database, db_user: dict | None = None) -> None:
    if not await ensure_auth(message, db_user):
        return

    if db_user["role"] == "intern":
        await message.answer("Для стажёра раздел заработка недоступен.")
        return

    total = await db.month_sales(db_user["id"])
    await message.answer(
        f"Ваш заработок за текущий месяц: {total:.2f}",
        reply_markup=earnings_menu(db_user["role"]),
    )
