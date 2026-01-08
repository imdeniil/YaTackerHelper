"""Тестовое меню для Owner - ручной запуск задач scheduler"""

import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from bot.database import get_session, UserCRUD
from bot.database.models import UserRole

logger = logging.getLogger(__name__)

testing_router = Router(name="testing")


@testing_router.message(Command("testing"))
async def cmd_testing(message: Message):
    """
    Тестовое меню для Owner.
    Позволяет вручную запускать задачи scheduler.
    """
    # Проверяем что пользователь - Owner
    async with get_session() as session:
        user = await UserCRUD.get_user_by_telegram_id(session, message.from_user.id)

        if not user or user.role != UserRole.OWNER:
            await message.answer("❌ Эта команда доступна только для Owner")
            return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🌅 Утренний список PENDING", callback_data="test_morning_pending")],
        [InlineKeyboardButton(text="⏰ Напоминание SCHEDULED_TODAY (18:00)", callback_data="test_reminder_today")],
        [InlineKeyboardButton(text="📅 Напоминание SCHEDULED_DATE (10:00)", callback_data="test_reminder_date")],
        [InlineKeyboardButton(text="🔄 Rollover SCHEDULED_TODAY", callback_data="test_rollover_today")],
        [InlineKeyboardButton(text="🔄 Rollover просроченных SCHEDULED_DATE", callback_data="test_rollover_date")],
        [InlineKeyboardButton(text="❌ Закрыть", callback_data="test_close")],
    ])

    await message.answer(
        "🧪 <b>Тестовое меню</b>\n\n"
        "Выберите задачу для ручного запуска:",
        reply_markup=keyboard,
    )


@testing_router.callback_query(F.data == "test_morning_pending")
async def test_morning_pending(callback: CallbackQuery):
    """Ручной запуск утреннего списка PENDING"""
    async with get_session() as session:
        user = await UserCRUD.get_user_by_telegram_id(session, callback.from_user.id)
        if not user or user.role != UserRole.OWNER:
            await callback.answer("❌ Недостаточно прав", show_alert=True)
            return

    await callback.answer("⏳ Запускаю...")

    try:
        from bot.services.payment_reminders import send_morning_pending_list
        await send_morning_pending_list(callback.bot)
        await callback.message.answer("✅ Утренний список PENDING отправлен billing контактам")
    except Exception as e:
        logger.error(f"Error in test_morning_pending: {e}", exc_info=True)
        await callback.message.answer(f"❌ Ошибка: {e}")


@testing_router.callback_query(F.data == "test_reminder_today")
async def test_reminder_today(callback: CallbackQuery):
    """Ручной запуск напоминания SCHEDULED_TODAY"""
    async with get_session() as session:
        user = await UserCRUD.get_user_by_telegram_id(session, callback.from_user.id)
        if not user or user.role != UserRole.OWNER:
            await callback.answer("❌ Недостаточно прав", show_alert=True)
            return

    await callback.answer("⏳ Запускаю...")

    try:
        from bot.services.payment_reminders import send_reminder_scheduled_today
        await send_reminder_scheduled_today(callback.bot)
        await callback.message.answer("✅ Напоминания SCHEDULED_TODAY отправлены")
    except Exception as e:
        logger.error(f"Error in test_reminder_today: {e}", exc_info=True)
        await callback.message.answer(f"❌ Ошибка: {e}")


@testing_router.callback_query(F.data == "test_reminder_date")
async def test_reminder_date(callback: CallbackQuery):
    """Ручной запуск напоминания SCHEDULED_DATE"""
    async with get_session() as session:
        user = await UserCRUD.get_user_by_telegram_id(session, callback.from_user.id)
        if not user or user.role != UserRole.OWNER:
            await callback.answer("❌ Недостаточно прав", show_alert=True)
            return

    await callback.answer("⏳ Запускаю...")

    try:
        from bot.services.payment_reminders import send_reminder_scheduled_date
        await send_reminder_scheduled_date(callback.bot)
        await callback.message.answer("✅ Напоминания SCHEDULED_DATE отправлены")
    except Exception as e:
        logger.error(f"Error in test_reminder_date: {e}", exc_info=True)
        await callback.message.answer(f"❌ Ошибка: {e}")


@testing_router.callback_query(F.data == "test_rollover_today")
async def test_rollover_today(callback: CallbackQuery):
    """Ручной запуск rollover SCHEDULED_TODAY"""
    async with get_session() as session:
        user = await UserCRUD.get_user_by_telegram_id(session, callback.from_user.id)
        if not user or user.role != UserRole.OWNER:
            await callback.answer("❌ Недостаточно прав", show_alert=True)
            return

    await callback.answer("⏳ Запускаю...")

    try:
        from bot.services.payment_reminders import rollover_scheduled_today
        await rollover_scheduled_today(callback.bot)
        await callback.message.answer("✅ Rollover SCHEDULED_TODAY выполнен")
    except Exception as e:
        logger.error(f"Error in test_rollover_today: {e}", exc_info=True)
        await callback.message.answer(f"❌ Ошибка: {e}")


@testing_router.callback_query(F.data == "test_rollover_date")
async def test_rollover_date(callback: CallbackQuery):
    """Ручной запуск rollover просроченных SCHEDULED_DATE"""
    async with get_session() as session:
        user = await UserCRUD.get_user_by_telegram_id(session, callback.from_user.id)
        if not user or user.role != UserRole.OWNER:
            await callback.answer("❌ Недостаточно прав", show_alert=True)
            return

    await callback.answer("⏳ Запускаю...")

    try:
        from bot.services.payment_reminders import rollover_overdue_scheduled_date
        await rollover_overdue_scheduled_date(callback.bot)
        await callback.message.answer("✅ Rollover просроченных SCHEDULED_DATE выполнен")
    except Exception as e:
        logger.error(f"Error in test_rollover_date: {e}", exc_info=True)
        await callback.message.answer(f"❌ Ошибка: {e}")


@testing_router.callback_query(F.data == "test_close")
async def test_close(callback: CallbackQuery):
    """Закрыть тестовое меню"""
    await callback.message.delete()
    await callback.answer()
