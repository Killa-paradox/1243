import logging

from aiogram import Router
from aiogram.types import ErrorEvent

router = Router()
logger = logging.getLogger(__name__)


@router.errors()
async def error_handler(event: ErrorEvent) -> bool:
    logger.exception("Unhandled error: %s", event.exception)
    if event.update.message:
        await event.update.message.answer("Произошла ошибка. Попробуйте позже.")
    return True
