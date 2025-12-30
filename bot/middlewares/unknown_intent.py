"""Middleware для обработки устаревших диалоговых окон"""
import logging
from typing import Callable, Dict, Any, Awaitable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, TelegramObject
from aiogram_dialog.api.exceptions import UnknownIntent
from aiogram_dialog import DialogManager, StartMode

from bot.states import MainMenu

logger = logging.getLogger(__name__)


class UnknownIntentMiddleware(BaseMiddleware):
    """Middleware для обработки UnknownIntent ошибок

    Обрабатывает случаи когда пользователь нажимает на кнопки в старых
    диалоговых окнах, контекст которых уже не существует (после перезапуска бота).
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        try:
            return await handler(event, data)
        except UnknownIntent as e:
            # Обрабатываем только callback query
            if not isinstance(event, CallbackQuery):
                raise

            logger.warning(f"UnknownIntent error for user {event.from_user.id}: {e}")

            # Получаем dialog_manager из data
            dialog_manager: DialogManager = data.get("dialog_manager")

            try:
                # Пытаемся удалить старое сообщение с устаревшими кнопками
                await event.message.delete()
            except Exception as delete_error:
                logger.debug(f"Could not delete old message: {delete_error}")

            # Отправляем новое сообщение и возвращаем в главное меню
            try:
                await event.message.answer(
                    "⚠️ <b>Это окно устарело</b>\n\n"
                    "Возвращаю вас в главное меню..."
                )

                # Запускаем главное меню
                if dialog_manager:
                    await dialog_manager.start(MainMenu.main, mode=StartMode.RESET_STACK)

            except Exception as msg_error:
                logger.error(f"Error sending fallback message: {msg_error}")

            # Отвечаем на callback чтобы убрать "часики" в Telegram
            await event.answer("Окно устарело, открываю главное меню")

            # Возвращаем None чтобы прервать дальнейшую обработку
            return None
