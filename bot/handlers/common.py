from aiogram import F, Router
from aiogram.types import Message

from ..db import Database
from ..keyboards.inline import earnings_menu
from ..keyboards.reply import MENU_EARNINGS, MENU_INFO, MENU_PROFILE, MENU_STAFF, MENU_STATS
from ..utils import format_staff_line

router = Router()


async def ensure_auth(message: Message, db_user: dict | None) -> bool:
    if not db_user:
        await message.answer("🔐 Сначала выполните /start и авторизуйтесь одноразовым паролем.")
        return False
    return True


@router.message(F.text == MENU_STAFF)
async def staff_info(message: Message, db: Database, db_user: dict | None = None) -> None:
    if not await ensure_auth(message, db_user):
        return

    staff = await db.all_staff()
    if not staff:
        await message.answer("👥 Список персонала пуст.")
        return

    lines = ["<b>👥 Весь персонал</b>"]
    for member in staff:
        lines.append(format_staff_line(member))
    await message.answer("\n\n".join(lines), parse_mode="HTML")


@router.message(F.text == MENU_PROFILE)
async def profile(message: Message, db: Database, db_user: dict | None = None) -> None:
    if not await ensure_auth(message, db_user):
        return

    month_sum = await db.month_sales(db_user["id"])
    status = "активен" if db_user["is_active"] else "неактивен"
    await message.answer(
        "\n".join(
            [
                "<b>🙍 Ваш профиль</b>",
                f"Имя аккаунта: {db_user['full_name'] or '-'}",
                f"Юзернейм: @{db_user['username'] or '-'}",
                f"Ранг: {db_user['role']}",
                f"Продажи за месяц: {month_sum:.2f}",
                f"Предупреждения: {db_user['warnings']}",
                f"Статус: {status}",
            ]
        ),
        parse_mode="HTML",
    )


@router.message(F.text == MENU_STATS)
async def stats(message: Message, db: Database, db_user: dict | None = None) -> None:
    if not await ensure_auth(message, db_user):
        return

    amount, count = await db.month_stats(db_user["id"])
    await message.answer(
        f"<b>📊 Статистика за месяц</b>\nСумма: <b>{amount:.2f}</b>\nКоличество подтверждённых продаж: <b>{count}</b>",
        parse_mode="HTML",
    )


@router.message(F.text == MENU_INFO)
async def info(message: Message, db_user: dict | None = None) -> None:
    if not await ensure_auth(message, db_user):
        return
    await message.answer(
        "<b>ℹ️ ALTShop Bot</b>\n"
        "• Работайте честно и прикладывайте подтверждения продаж.\n"
        "• По вопросам: @altshop_admin",
        parse_mode="HTML",
    )


@router.message(F.text == MENU_EARNINGS)
async def month_earnings(message: Message, db: Database, db_user: dict | None = None) -> None:
    if not await ensure_auth(message, db_user):
        return

    if db_user["role"] == "intern":
        await message.answer("⛔ Для стажёра раздел заработка недоступен.")
        return

    total = await db.month_sales(db_user["id"])
    await message.answer(
        f"<b>💰 Ваш заработок за текущий месяц:</b> <code>{total:.2f}</code>",
        parse_mode="HTML",
        reply_markup=earnings_menu(db_user["role"]),
    )
