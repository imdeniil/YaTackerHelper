"""Error handler для обработки устаревших диалоговых окон"""
import logging

from aiogram import Router, F
from aiogram.types import ErrorEvent, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
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
        # Редактируем сообщение и добавляем кнопку удаления
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🗑 Удалить", callback_data="delete_expired_message")]
        ])

        await callback.message.edit_text(
            text=(
                "⚠️ <b>Это окно устарело</b>\n\n"
                "Используйте команду /start для возврата в главное меню."
            ),
            reply_markup=keyboard
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


@unknown_intent_router.callback_query(F.data == "delete_expired_message")
async def delete_expired_message(callback: CallbackQuery):
    """Обработчик кнопки удаления устаревшего сообщения"""
    try:
        await callback.message.delete()
        await callback.answer("Сообщение удалено")
    except Exception as e:
        logger.error(f"Error deleting expired message: {e}")
        await callback.answer("Не удалось удалить сообщение")
