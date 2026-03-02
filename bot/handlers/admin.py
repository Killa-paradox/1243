from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from ..db import Database
from ..keyboards.inline import admin_panel, role_picker, user_picker
from ..keyboards.reply import MENU_ADMIN
from ..states import AdminAddMemberStates
from ..utils import format_staff_line, generate_one_time_password

router = Router()


def _admin_only(user: dict | None) -> bool:
    return bool(user and user["role"] == "admin")


@router.message(F.text == MENU_ADMIN)
async def admin_menu(message: Message, db_user: dict | None = None) -> None:
    if not _admin_only(db_user):
        await message.answer("⛔ Раздел доступен только администраторам.")
        return
    await message.answer("<b>🛠 Админ-панель</b>\nВыберите действие:", parse_mode="HTML", reply_markup=admin_panel())


@router.message(Command("admin"))
async def admin_menu_cmd(message: Message, db_user: dict | None = None) -> None:
    await admin_menu(message, db_user)


@router.callback_query(F.data == "admin_add_member")
async def admin_add_member(callback: CallbackQuery, state: FSMContext, db_user: dict | None = None) -> None:
    if not _admin_only(db_user):
        await callback.answer("Недостаточно прав", show_alert=True)
        return
    await state.set_state(AdminAddMemberStates.waiting_role)
    await callback.message.answer("<b>➕ Добавление участника</b>\nВыберите ранг:", parse_mode="HTML", reply_markup=role_picker("newmember"))
    await callback.answer()


@router.callback_query(AdminAddMemberStates.waiting_role, F.data.startswith("newmember:"))
async def admin_add_member_role(callback: CallbackQuery, state: FSMContext) -> None:
    role = callback.data.split(":")[1]
    await state.update_data(role=role)
    await state.set_state(AdminAddMemberStates.waiting_name)
    await callback.message.answer("Введите <b>имя аккаунта</b> для участника:", parse_mode="HTML")
    await callback.answer()


@router.message(AdminAddMemberStates.waiting_name)
async def admin_add_member_name(message: Message, state: FSMContext, db: Database, db_user: dict | None = None) -> None:
    if not _admin_only(db_user):
        await message.answer("⛔ Недостаточно прав")
        return
    if not message.text:
        return

    data = await state.get_data()
    role = data["role"]
    account_name = message.text.strip()
    password = generate_one_time_password()
    await db.create_member(role=role, full_name=account_name, raw_password=password)
    await state.clear()
    await message.answer(
        f"<b>✅ Участник создан</b>\nРанг: <b>{role}</b>\nИмя аккаунта: <b>{account_name}</b>\n"
        f"Одноразовый пароль: <code>{password}</code>\nПередайте пароль сотруднику.",
        parse_mode="HTML",
    )


@router.callback_query(F.data == "admin_warn_member")
async def start_warn(callback: CallbackQuery, db: Database, db_user: dict | None = None) -> None:
    if not _admin_only(db_user):
        await callback.answer("Недостаточно прав", show_alert=True)
        return
    users = await db.list_users_for_warning()
    await callback.message.answer("⚠️ Выберите участника для предупреждения:", reply_markup=user_picker("warn", users))
    await callback.answer()


@router.callback_query(F.data.startswith("warn:"))
async def warn_member(callback: CallbackQuery, db: Database, db_user: dict | None = None) -> None:
    if not _admin_only(db_user):
        await callback.answer("Недостаточно прав", show_alert=True)
        return

    user_id = int(callback.data.split(":")[1])
    updated = await db.issue_warning(user_id)
    if not updated:
        await callback.message.answer("Нельзя выдать предупреждение этому пользователю.")
        await callback.answer()
        return

    await callback.message.answer(
        f"⚠️ Предупреждение выдано: {updated['full_name']}. Всего предупреждений: {updated['warnings']}"
    )
    if updated["user_id"]:
        await callback.bot.send_message(
            updated["user_id"],
            f"⚠️ Вам выдано предупреждение. Текущее число: {updated['warnings']}."
            + (" Вы были автоматически заблокированы." if not updated["is_active"] else ""),
        )
    await callback.answer()


@router.callback_query(F.data == "admin_toggle_block")
async def toggle_block_menu(callback: CallbackQuery, db: Database, db_user: dict | None = None) -> None:
    if not _admin_only(db_user):
        await callback.answer("Недостаточно прав", show_alert=True)
        return
    users = await db.list_users()
    await callback.message.answer("🔒 Выберите участника для смены статуса:", reply_markup=user_picker("block", users))
    await callback.answer()


@router.callback_query(F.data.startswith("block:"))
async def toggle_block(callback: CallbackQuery, db: Database, db_user: dict | None = None) -> None:
    if not _admin_only(db_user):
        await callback.answer("Недостаточно прав", show_alert=True)
        return
    target_id = int(callback.data.split(":")[1])
    users = await db.list_users()
    target = next((u for u in users if u["id"] == target_id), None)
    if not target:
        await callback.answer("Пользователь не найден", show_alert=True)
        return
    new_state = not bool(target["is_active"])
    await db.set_block_status(target_id, new_state)
    await callback.message.answer(
        f"{'✅' if new_state else '⛔'} Пользователь {target['full_name']} теперь {'активен' if new_state else 'неактивен'}."
    )
    if target["user_id"]:
        await callback.bot.send_message(
            target["user_id"],
            f"Ваш статус изменён администратором: {'активен' if new_state else 'неактивен'}.",
        )
    await callback.answer()


@router.callback_query(F.data == "admin_staff")
async def staff_list(callback: CallbackQuery, db: Database, db_user: dict | None = None) -> None:
    if not _admin_only(db_user):
        await callback.answer("Недостаточно прав", show_alert=True)
        return
    users = await db.list_users()
    if not users:
        await callback.message.answer("Список персонала пуст.")
        await callback.answer()
        return
    lines = ["<b>👥 Состав персонала</b>"]
    for u in users:
        lines.append(format_staff_line(u))
    await callback.message.answer("\n\n".join(lines), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "admin_sales_history")
async def admin_sales_history(callback: CallbackQuery, db: Database, db_user: dict | None = None) -> None:
    if not _admin_only(db_user):
        await callback.answer("Недостаточно прав", show_alert=True)
        return
    users = await db.list_users()
    await callback.message.answer(
        "📈 Выберите сотрудника для просмотра истории продаж:", reply_markup=user_picker("salesfor", users)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("salesfor:"))
async def admin_sales_for_user(callback: CallbackQuery, db: Database, db_user: dict | None = None) -> None:
    if not _admin_only(db_user):
        await callback.answer("Недостаточно прав", show_alert=True)
        return
    target_id = int(callback.data.split(":")[1])
    users = await db.list_users()
    target = next((u for u in users if u["id"] == target_id), None)
    if not target:
        await callback.answer("Пользователь не найден", show_alert=True)
        return
    sales = await db.month_sales_for_user_id(target_id)
    if not sales:
        await callback.message.answer(f"У {target['full_name']} нет продаж в этом месяце.")
    else:
        text = [f"📈 Продажи {target['full_name']}:"]
        for s in sales[:30]:
            text.append(f"#{s['id']} | {s['amount']:.2f} | {s['status']} | {s['created_at']}")
        await callback.message.answer("\n".join(text))
    await callback.answer()


@router.callback_query(F.data == "noop")
async def noop(callback: CallbackQuery) -> None:
    await callback.answer()
