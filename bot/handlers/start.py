from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from ..db import Database
from ..keyboards.reply import main_menu
from ..states import AuthStates

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, db: Database, db_user: dict | None = None) -> None:
    if db_user:
        if not db_user["is_active"]:
            await message.answer("Ваш аккаунт заблокирован. Обратитесь к администратору.")
            return
        await message.answer("Вы уже авторизованы.", reply_markup=main_menu(db_user["role"]))
        return

    await state.set_state(AuthStates.waiting_password)
    await message.answer("Добро пожаловать в ALTShop Bot. Введите одноразовый пароль:")


@router.message(AuthStates.waiting_password)
async def auth_by_password(message: Message, state: FSMContext, db: Database) -> None:
    if not message.from_user or not message.text:
        return

    user = await db.bind_user_with_password(
        tg_id=message.from_user.id,
        username=message.from_user.username,
        full_name=message.from_user.full_name,
        raw_password=message.text.strip(),
    )
    if not user:
        await message.answer("Неверный пароль. Попробуйте снова.")
        return

    await state.clear()
    await message.answer(
        f"Успешная авторизация. Ваша роль: {user['role']}",
        reply_markup=main_menu(user["role"]),
    )
