from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject

from .db import Database


class AuthMiddleware(BaseMiddleware):
    def __init__(self, db: Database) -> None:
        self.db = db

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = None
        if isinstance(event, Message) and event.from_user:
            user = await self.db.get_user_by_telegram_id(event.from_user.id)
            data["db_user"] = user

            if user and not user["is_active"] and event.text != "/start":
                await event.answer("Ваш аккаунт заблокирован. Обратитесь к администратору.")
                return

        return await handler(event, data)
