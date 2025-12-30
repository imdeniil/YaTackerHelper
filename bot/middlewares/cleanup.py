"""Middleware для автоматического удаления сообщений пользователя"""
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject


class MessageCleanupMiddleware(BaseMiddleware):
    """Middleware для удаления сообщений пользователя в диалогах

    Автоматически удаляет все сообщения пользователя (текст, документы, фото) после их обработки.
    Это позволяет реализовать single window интерфейс без ручного удаления.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        # Выполняем основную обработку
        result = await handler(event, data)

        # Удаляем сообщение пользователя после обработки (текст, документы, фото и т.д.)
        if isinstance(event, Message) and not event.from_user.is_bot:
            try:
                await event.delete()
            except Exception:
                pass  # Игнорируем ошибки удаления

        return result
