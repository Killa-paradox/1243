from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InputMediaPhoto, Message

from ..db import Database
from ..keyboards.inline import done_screenshots_button, sale_decision_kb
from ..states import AddSaleStates

router = Router()


@router.callback_query(F.data == "sale_add")
async def start_add_sale(callback: CallbackQuery, state: FSMContext, db_user: dict | None = None) -> None:
    if not db_user:
        await callback.message.answer("Сначала авторизуйтесь через /start")
        await callback.answer()
        return

    if db_user["role"] == "intern":
        await callback.message.answer("Функция недоступна для роли intern.")
        await callback.answer()
        return

    await state.set_state(AddSaleStates.waiting_amount)
    await callback.message.answer("Введите сумму продажи (например 1500.50)")
    await callback.answer()


@router.message(AddSaleStates.waiting_amount)
async def get_sale_amount(message: Message, state: FSMContext) -> None:
    if not message.text:
        return
    try:
        amount = float(message.text.replace(",", "."))
        if amount <= 0:
            raise ValueError
    except ValueError:
        await message.answer("Введите корректную сумму (число больше 0).")
        return

    await state.update_data(amount=amount, screenshots=[])
    await state.set_state(AddSaleStates.waiting_screenshots)
    await message.answer(
        "Отправьте один или несколько скриншотов продажи, затем нажмите «Готово».",
        reply_markup=done_screenshots_button(),
    )


@router.message(AddSaleStates.waiting_screenshots, F.photo)
async def collect_screenshots(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    screenshots: list[str] = data.get("screenshots", [])
    screenshots.append(message.photo[-1].file_id)
    await state.update_data(screenshots=screenshots)
    await message.answer(f"Скриншот добавлен. Всего: {len(screenshots)}")


@router.callback_query(AddSaleStates.waiting_screenshots, F.data == "sale_done")
async def finish_sale(callback: CallbackQuery, state: FSMContext, db: Database, db_user: dict | None = None) -> None:
    if not db_user:
        await callback.answer()
        return

    data = await state.get_data()
    amount = data.get("amount")
    screenshots = data.get("screenshots", [])

    if not screenshots:
        await callback.message.answer("Добавьте хотя бы один скриншот.")
        await callback.answer()
        return

    sale_id = await db.create_sale(user_db_id=db_user["id"], amount=amount, screenshots=screenshots)
    admins = await db.get_admins()

    caption = (
        f"Новая продажа #{sale_id}\n"
        f"Продавец: {db_user['full_name']} (@{db_user['username'] or '-'})\n"
        f"Telegram ID: {db_user['user_id']}\n"
        f"Сумма: {amount:.2f}"
    )

    for admin in admins:
        if not admin["user_id"]:
            continue
        media = [InputMediaPhoto(media=screenshots[0], caption=caption)]
        media.extend(InputMediaPhoto(media=photo) for photo in screenshots[1:])
        await callback.bot.send_media_group(chat_id=admin["user_id"], media=media)
        await callback.bot.send_message(
            chat_id=admin["user_id"],
            text=f"Модерация продажи #{sale_id}",
            reply_markup=sale_decision_kb(sale_id),
        )

    await state.clear()
    await callback.message.answer("Продажа отправлена администраторам на проверку.")
    await callback.answer()


@router.callback_query(F.data.startswith("sales_history_me"))
async def my_sales_history(callback: CallbackQuery, db: Database, db_user: dict | None = None) -> None:
    if not db_user:
        await callback.answer()
        return
    sales = await db.month_sales_for_user_id(db_user["id"])
    if not sales:
        await callback.message.answer("За текущий месяц продаж пока нет.")
    else:
        text = ["История продаж за месяц:"]
        for s in sales[:20]:
            text.append(f"#{s['id']} | {s['amount']:.2f} | {s['status']} | {s['created_at']}")
        await callback.message.answer("\n".join(text))
    await callback.answer()


@router.callback_query(F.data.startswith("sale_approve:"))
async def approve_sale(callback: CallbackQuery, db: Database, db_user: dict | None = None) -> None:
    if not db_user or db_user["role"] != "admin":
        await callback.answer("Недостаточно прав", show_alert=True)
        return
    sale_id = int(callback.data.split(":")[1])
    sale = await db.get_sale(sale_id)
    if not sale:
        await callback.answer("Продажа не найдена", show_alert=True)
        return
    await db.update_sale_status(sale_id, "approved", db_user["id"])
    seller = await _get_user_by_db_id(db, sale["user_id"])
    if seller and seller["user_id"]:
        await callback.bot.send_message(seller["user_id"], f"Ваша продажа #{sale_id} одобрена ✅")
    await callback.message.answer(f"Продажа #{sale_id} подтверждена.")
    await callback.answer()


@router.callback_query(F.data.startswith("sale_need_more:"))
async def need_more_sale(callback: CallbackQuery, db: Database, db_user: dict | None = None) -> None:
    if not db_user or db_user["role"] != "admin":
        await callback.answer("Недостаточно прав", show_alert=True)
        return
    sale_id = int(callback.data.split(":")[1])
    sale = await db.get_sale(sale_id)
    if not sale:
        await callback.answer("Продажа не найдена", show_alert=True)
        return
    await db.update_sale_status(sale_id, "need_more", db_user["id"])
    seller = await _get_user_by_db_id(db, sale["user_id"])
    if seller and seller["user_id"]:
        await callback.bot.send_message(
            seller["user_id"],
            f"По продаже #{sale_id} требуется дополнительная проверка. Пришлите обновлённые материалы администратору.",
        )
    await callback.message.answer(f"По продаже #{sale_id} запрошена доп. проверка.")
    await callback.answer()


@router.callback_query(F.data.startswith("sale_reject:"))
async def reject_sale(callback: CallbackQuery, db: Database, db_user: dict | None = None) -> None:
    if not db_user or db_user["role"] != "admin":
        await callback.answer("Недостаточно прав", show_alert=True)
        return
    sale_id = int(callback.data.split(":")[1])
    sale = await db.get_sale(sale_id)
    if not sale:
        await callback.answer("Продажа не найдена", show_alert=True)
        return
    await db.update_sale_status(sale_id, "rejected", db_user["id"])
    seller = await _get_user_by_db_id(db, sale["user_id"])
    if seller and seller["user_id"]:
        await callback.bot.send_message(seller["user_id"], f"Ваша продажа #{sale_id} отклонена ❌")
    await callback.message.answer(f"Продажа #{sale_id} отклонена.")
    await callback.answer()


async def _get_user_by_db_id(db: Database, user_db_id: int) -> dict | None:
    users = await db.list_users()
    for user in users:
        if user["id"] == user_db_id:
            return user
    return None
