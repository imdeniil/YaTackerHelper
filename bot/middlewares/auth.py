"""Middleware для авторизации пользователей"""
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Update, Message
from bot.database import get_session, UserCRUD


class AuthMiddleware(BaseMiddleware):
    """Middleware для проверки авторизации пользователя

    Проверяет что пользователь существует в БД перед обработкой любого update.
    При первом входе связывает пользователя по username с его telegram_id.
    Если пользователь не найден - отправляет сообщение об ошибке и блокирует обработку.

    Добавляет в event_context["middleware_data"]:
        - user: объект User из БД
        - user_settings: объект UserSettings из БД
    """

    async def __call__(
        self,
        handler: Callable[[Update, Dict[str, Any]], Awaitable[Any]],
        event: Update,
        data: Dict[str, Any],
    ) -> Any:
        # Извлекаем telegram_id и username из различных типов событий
        telegram_id = None
        telegram_username = None

        if event.message:
            telegram_id = event.message.from_user.id
            telegram_username = event.message.from_user.username
        elif event.callback_query:
            telegram_id = event.callback_query.from_user.id
            telegram_username = event.callback_query.from_user.username
        elif hasattr(event, "from_user") and event.from_user:
            telegram_id = event.from_user.id
            telegram_username = event.from_user.username

        # Если не удалось извлечь telegram_id - пропускаем
        if not telegram_id:
            return await handler(event, data)

        # Проверяем пользователя в БД
        async with get_session() as session:
            # Сначала ищем по telegram_id
            user = await UserCRUD.get_user_by_telegram_id(session, telegram_id)

            # Если не найден по ID, но есть username - ищем по username
            if not user and telegram_username:
                user = await UserCRUD.get_user_by_username(session, telegram_username)

                # Если нашли по username - связываем с telegram_id (первый вход)
                if user:
                    user = await UserCRUD.update_user(
                        session,
                        user.id,
                        telegram_id=telegram_id,
                        telegram_username=telegram_username
                    )

            if not user:
                # Пользователь не авторизован - отправляем сообщение об ошибке
                await self._send_unauthorized_message(event)
                return  # Блокируем дальнейшую обработку

            # Проверяем активность пользователя
            if not user.is_active:
                await self._send_deactivated_message(event)
                return  # Блокируем дальнейшую обработку

            # Добавляем пользователя и настройки в middleware_data
            data["user"] = user
            data["user_settings"] = user.settings

        # Продолжаем обработку
        return await handler(event, data)

    async def _send_unauthorized_message(self, event: Update) -> None:
        """Отправляет сообщение о том что пользователь не авторизован"""
        message_text = (
            "❌ Доступ запрещен\n\n"
            "Вы не авторизованы для использования этого бота.\n"
            "Обратитесь к владельцу для получения доступа."
        )

        # Отправляем сообщение в зависимости от типа события
        if event.message:
            await event.message.answer(message_text)
        elif event.callback_query:
            await event.callback_query.answer(message_text, show_alert=True)

    async def _send_deactivated_message(self, event: Update) -> None:
        """Отправляет сообщение о том что аккаунт пользователя деактивирован"""
        message_text = (
            "❌ Аккаунт деактивирован\n\n"
            "Ваш аккаунт был деактивирован.\n"
            "Обратитесь к владельцу для восстановления доступа."
        )

        # Отправляем сообщение в зависимости от типа события
        if event.message:
            await event.message.answer(message_text)
        elif event.callback_query:
            await event.callback_query.answer(message_text, show_alert=True)
