"""Error handler для обработки устаревших диалоговых окон"""
import logging

from aiogram import Router
from aiogram.types import ErrorEvent, CallbackQuery
from aiogram_dialog.api.exceptions import UnknownIntent

logger = logging.getLogger(__name__)

# Router для error handler
unknown_intent_router = Router()


@unknown_intent_router.error()
async def handle_unknown_intent(event: ErrorEvent):
    """Error handler для UnknownIntent исключений

    Обрабатывает случаи когда пользователь нажимает на кнопки в старых
    диалоговых окнах, контекст которых уже не существует (после перезапуска бота).
    """
    # Проверяем что это UnknownIntent ошибка
    if not isinstance(event.exception, UnknownIntent):
        return

    # Обрабатываем только callback query
    if not isinstance(event.update.callback_query, CallbackQuery):
        return

    callback = event.update.callback_query

    logger.warning(f"UnknownIntent error for user {callback.from_user.id}: {event.exception}")

    try:
        # Редактируем сообщение и удаляем кнопки
        await callback.message.edit_text(
            text=(
                "⚠️ <b>Это окно устарело</b>\n\n"
                "Используйте команду /start для возврата в главное меню."
            ),
            reply_markup=None  # Удаляем кнопки
        )
    except Exception as edit_error:
        logger.error(f"Error editing message: {edit_error}")
        # Если не удалось отредактировать - пробуем удалить и отправить новое
        try:
            await callback.message.delete()
            await callback.message.answer(
                "⚠️ <b>Это окно устарело</b>\n\n"
                "Используйте команду /start для возврата в главное меню."
            )
        except Exception:
            pass

    # Отвечаем на callback чтобы убрать "часики" в Telegram
    try:
        await callback.answer("Окно устарело, используйте /start")
    except Exception:
        pass

    # Возвращаем True чтобы отметить ошибку как обработанную
    return True
