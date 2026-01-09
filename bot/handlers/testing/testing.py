"""Тестовое меню для Owner - ручной запуск задач scheduler"""

import logging
from datetime import datetime, timedelta
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from bot.database.models import UserRole, PaymentRequestStatus
from bot.database import get_session, PaymentRequestCRUD

logger = logging.getLogger(__name__)

testing_router = Router(name="testing")


@testing_router.message(Command("testing"))
async def cmd_testing(message: Message, user=None):
    """
    Тестовое меню для Owner.
    Позволяет вручную запускать задачи scheduler.
    """
    logger.info(f"cmd_testing called by {message.from_user.id}, user={user}")

    # Проверяем что пользователь - Owner
    if not user or user.role != UserRole.OWNER:
        await message.answer("❌ Эта команда доступна только для Owner")
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        # Тестовые данные
        [InlineKeyboardButton(text="📦 ТЕСТОВЫЕ ДАННЫЕ", callback_data="test_noop")],
        [InlineKeyboardButton(text="📝 Создать тестовые платежи", callback_data="test_create_payments")],
        [InlineKeyboardButton(text="🗑 Удалить все платежи", callback_data="test_delete_payments")],

        # Уведомления Владелец/Менеджер (billing)
        [InlineKeyboardButton(text="👑 ВЛАДЕЛЕЦ / МЕНЕДЖЕР", callback_data="test_noop")],
        [InlineKeyboardButton(text="🌅 Утренний список PENDING", callback_data="test_morning_pending")],
        [InlineKeyboardButton(text="⏰ Напоминание SCHEDULED_TODAY (18:00)", callback_data="test_reminder_today")],
        [InlineKeyboardButton(text="📅 Напоминание SCHEDULED_DATE (10:00)", callback_data="test_reminder_date")],
        [InlineKeyboardButton(text="🔄 Rollover SCHEDULED_TODAY", callback_data="test_rollover_today")],
        [InlineKeyboardButton(text="🔄 Rollover просроченных SCHEDULED_DATE", callback_data="test_rollover_date")],

        # Уведомления Сотрудник (worker)
        [InlineKeyboardButton(text="👷 СОТРУДНИК", callback_data="test_noop")],
        [InlineKeyboardButton(text="✅ Уведомление об оплате", callback_data="test_worker_paid")],
        [InlineKeyboardButton(text="📅 Уведомление о планировании", callback_data="test_worker_scheduled")],
        [InlineKeyboardButton(text="❌ Уведомление об отмене", callback_data="test_worker_cancelled")],
        [InlineKeyboardButton(text="⚠️ Напоминание о неоплате", callback_data="test_worker_overdue_reminder")],

        [InlineKeyboardButton(text="❌ Закрыть", callback_data="test_close")],
    ])

    await message.answer(
        "🧪 <b>Тестовое меню</b>\n\n"
        "📦 <b>Тестовые данные</b> — создание/удаление платежей\n"
        "👑 <b>Владелец/Менеджер</b> — уведомления billing контактам\n"
        "👷 <b>Сотрудник</b> — уведомления создателям запросов\n\n"
        "Выберите действие:",
        reply_markup=keyboard,
    )


@testing_router.callback_query(F.data == "test_morning_pending")
async def test_morning_pending(callback: CallbackQuery, user=None):
    """Ручной запуск утреннего списка PENDING"""
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
async def test_reminder_today(callback: CallbackQuery, user=None):
    """Ручной запуск напоминания SCHEDULED_TODAY"""
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
async def test_reminder_date(callback: CallbackQuery, user=None):
    """Ручной запуск напоминания SCHEDULED_DATE"""
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
async def test_rollover_today(callback: CallbackQuery, user=None):
    """Ручной запуск rollover SCHEDULED_TODAY"""
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
async def test_rollover_date(callback: CallbackQuery, user=None):
    """Ручной запуск rollover просроченных SCHEDULED_DATE"""
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


@testing_router.callback_query(F.data == "test_noop")
async def test_noop(callback: CallbackQuery):
    """Пустой обработчик для разделителя"""
    await callback.answer()


@testing_router.callback_query(F.data == "test_create_payments")
async def test_create_payments(callback: CallbackQuery, user=None):
    """Создание тестовых платежей для презентации"""
    if not user or user.role != UserRole.OWNER:
        await callback.answer("❌ Недостаточно прав", show_alert=True)
        return

    await callback.answer("⏳ Создаю тестовые платежи...")

    try:
        now = datetime.utcnow()
        today = now.date()

        # Реальные file_id из Telegram (из выгрузки тестов)
        INVOICE_FILE_IDS = [
            "BQACAgIAAxkDAAII7mlUX3a-423IKbbevnekTRtNUkWeAAIJiQAC_1upSqr8F7DyVYcTOAQ",
            "BQACAgIAAxkBAAIIWmlTUMp_0VjbxzsCvji2nBrr8I9dAAIklAAC12mYSoEoeLdTEia_OAQ",
            "BQACAgIAAxkDAAIJu2lfmXs63K5OQyi12NR7Z8BDrMSrAALNmAACxfoBSwWYXwQ1A9MCOAQ",
        ]
        PAYMENT_PROOF_FILE_IDS = [
            "BQACAgIAAxkBAAIJfGlUfohaSk4AAWwHmET-KrkIPRCfkgACxIwAAsMMoEqbbewnF4cenDgE",
            "BQACAgIAAxkBAAIJcGlUfV2C6rLVeujO8qeJIOUPT2cqAALDjAACywygSv9BE1uzGJzJOAQ",
            "BQACAgIAAxkDAAIJvWlfon7T_dX-D8Sq4_hZw5k2xO8eAAJimQACxfoBS2sSJ6PGDVadOAQ",
        ]

        # Тестовые данные для презентации
        test_payments = [
            # PENDING - новые запросы
            {
                "title": "Оплата хостинга Selectel",
                "amount": "15 000",
                "comment": "Ежемесячная оплата серверов и хранилища",
                "status": PaymentRequestStatus.PENDING,
                "created_at": now - timedelta(hours=2),
                "invoice_file_id": INVOICE_FILE_IDS[0],
            },
            {
                "title": "Лицензия 1C:Предприятие",
                "amount": "85 500",
                "comment": "Продление годовой лицензии на 5 рабочих мест",
                "status": PaymentRequestStatus.PENDING,
                "created_at": now - timedelta(days=1),
                "invoice_file_id": INVOICE_FILE_IDS[1],
            },
            {
                "title": "Закупка оборудования",
                "amount": "450 000",
                "comment": "Новые MacBook Pro для отдела разработки (3 шт)",
                "status": PaymentRequestStatus.PENDING,
                "created_at": now - timedelta(days=2),
                "invoice_file_id": INVOICE_FILE_IDS[2],
            },

            # SCHEDULED_TODAY - на сегодня
            {
                "title": "Аренда офиса",
                "amount": "150 000",
                "comment": "Ежемесячная аренда офисного помещения",
                "status": PaymentRequestStatus.SCHEDULED_TODAY,
                "created_at": now - timedelta(days=3),
                "invoice_file_id": INVOICE_FILE_IDS[0],
            },

            # SCHEDULED_DATE - на будущие даты
            {
                "title": "Реклама Яндекс.Директ",
                "amount": "50 000",
                "comment": "Пополнение рекламного бюджета",
                "status": PaymentRequestStatus.SCHEDULED_DATE,
                "scheduled_date": today + timedelta(days=3),
                "created_at": now - timedelta(days=1),
                "invoice_file_id": INVOICE_FILE_IDS[1],
            },
            {
                "title": "Зарплата подрядчику",
                "amount": "230 000",
                "comment": "Разработка мобильного приложения - этап 2",
                "status": PaymentRequestStatus.SCHEDULED_DATE,
                "scheduled_date": today + timedelta(days=7),
                "created_at": now - timedelta(days=5),
                "invoice_file_id": INVOICE_FILE_IDS[2],
            },

            # PAID - оплаченные
            {
                "title": "Канцелярия",
                "amount": "3 500",
                "comment": "Бумага, ручки, папки для офиса",
                "status": PaymentRequestStatus.PAID,
                "created_at": now - timedelta(days=2),
                "paid_at": now - timedelta(days=1),
                "invoice_file_id": INVOICE_FILE_IDS[0],
                "payment_proof_file_id": PAYMENT_PROOF_FILE_IDS[0],
            },
            {
                "title": "Курьерская доставка СДЭК",
                "amount": "1 200",
                "comment": "Доставка документов клиенту",
                "status": PaymentRequestStatus.PAID,
                "created_at": now - timedelta(days=4),
                "paid_at": now - timedelta(days=3),
                "invoice_file_id": INVOICE_FILE_IDS[1],
                "payment_proof_file_id": PAYMENT_PROOF_FILE_IDS[1],
            },
            {
                "title": "Подписка Figma",
                "amount": "12 000",
                "comment": "Годовая подписка Professional на 2 места",
                "status": PaymentRequestStatus.PAID,
                "created_at": now - timedelta(days=10),
                "paid_at": now - timedelta(days=7),
                "invoice_file_id": INVOICE_FILE_IDS[2],
                "payment_proof_file_id": PAYMENT_PROOF_FILE_IDS[2],
            },

            # CANCELLED - отменённые
            {
                "title": "Отменённый заказ оборудования",
                "amount": "25 000",
                "comment": "Заказ отменён по причине изменения требований",
                "status": PaymentRequestStatus.CANCELLED,
                "created_at": now - timedelta(days=5),
                "invoice_file_id": INVOICE_FILE_IDS[0],
            },
        ]

        created_count = 0
        async with get_session() as session:
            for payment_data in test_payments:
                # Создаём запрос напрямую через модель
                from bot.database.models import PaymentRequest
                payment = PaymentRequest(
                    created_by_id=user.id,
                    title=payment_data["title"],
                    amount=payment_data["amount"],
                    comment=payment_data["comment"],
                    status=payment_data["status"],
                    created_at=payment_data.get("created_at", now),
                    scheduled_date=payment_data.get("scheduled_date"),
                    paid_at=payment_data.get("paid_at"),
                    paid_by_id=user.id if payment_data.get("paid_at") else None,
                    invoice_file_id=payment_data.get("invoice_file_id"),
                    payment_proof_file_id=payment_data.get("payment_proof_file_id"),
                )
                session.add(payment)
                created_count += 1

            await session.commit()

        await callback.message.answer(
            f"✅ Создано {created_count} тестовых платежей:\n\n"
            f"• PENDING: 3\n"
            f"• SCHEDULED_TODAY: 1\n"
            f"• SCHEDULED_DATE: 2\n"
            f"• PAID: 3\n"
            f"• CANCELLED: 1"
        )
    except Exception as e:
        logger.error(f"Error in test_create_payments: {e}", exc_info=True)
        await callback.message.answer(f"❌ Ошибка: {e}")


@testing_router.callback_query(F.data == "test_delete_payments")
async def test_delete_payments(callback: CallbackQuery, user=None):
    """Удаление всех платежей"""
    if not user or user.role != UserRole.OWNER:
        await callback.answer("❌ Недостаточно прав", show_alert=True)
        return

    # Запрашиваем подтверждение
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Да, удалить всё", callback_data="test_delete_payments_confirm"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="test_close"),
        ],
    ])

    await callback.message.edit_text(
        "⚠️ <b>Вы уверены?</b>\n\n"
        "Это действие удалит ВСЕ платежи из базы данных.\n"
        "Отменить это действие будет невозможно!",
        reply_markup=keyboard,
    )
    await callback.answer()


@testing_router.callback_query(F.data == "test_delete_payments_confirm")
async def test_delete_payments_confirm(callback: CallbackQuery, user=None):
    """Подтверждение удаления всех платежей"""
    if not user or user.role != UserRole.OWNER:
        await callback.answer("❌ Недостаточно прав", show_alert=True)
        return

    await callback.answer("⏳ Удаляю...")

    try:
        from sqlalchemy import delete
        from bot.database.models import PaymentRequest, BillingNotification

        async with get_session() as session:
            # Сначала удаляем уведомления
            await session.execute(delete(BillingNotification))
            # Затем платежи
            result = await session.execute(delete(PaymentRequest))
            deleted_count = result.rowcount
            await session.commit()

        await callback.message.edit_text(
            f"✅ Удалено {deleted_count} платежей"
        )
    except Exception as e:
        logger.error(f"Error in test_delete_payments_confirm: {e}", exc_info=True)
        await callback.message.answer(f"❌ Ошибка: {e}")


# ============ Тестовые уведомления для Сотрудника ============

@testing_router.callback_query(F.data == "test_worker_paid")
async def test_worker_paid(callback: CallbackQuery, user=None):
    """Тестовое уведомление сотруднику об оплате запроса"""
    if not user or user.role != UserRole.OWNER:
        await callback.answer("❌ Недостаточно прав", show_alert=True)
        return

    await callback.answer("⏳ Отправляю...")

    try:
        # Пример уведомления об оплате
        worker_text = (
            f"✅ <b>Ваш запрос на оплату #123 оплачен!</b>\n\n"
            f"<b>Название:</b> Оплата хостинга Selectel\n"
            f"<b>Сумма:</b> 15 000 ₽\n"
            f"<b>Оплатил:</b> {user.display_name}\n"
            f"<b>Дата оплаты:</b> {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
            f"Платежный документ прикреплен ниже."
        )

        await callback.message.answer(worker_text)
        await callback.message.answer("📎 [Здесь был бы прикреплён платёжный документ]")

    except Exception as e:
        logger.error(f"Error in test_worker_paid: {e}", exc_info=True)
        await callback.message.answer(f"❌ Ошибка: {e}")


@testing_router.callback_query(F.data == "test_worker_scheduled")
async def test_worker_scheduled(callback: CallbackQuery, user=None):
    """Тестовое уведомление сотруднику о планировании запроса"""
    if not user or user.role != UserRole.OWNER:
        await callback.answer("❌ Недостаточно прав", show_alert=True)
        return

    await callback.answer("⏳ Отправляю...")

    try:
        scheduled_date = (datetime.now() + timedelta(days=3)).strftime('%d.%m.%Y')

        # Пример уведомления о планировании на дату
        worker_text_date = (
            f"📅 <b>Запрос на оплату #124 запланирован</b>\n\n"
            f"<b>Название:</b> Лицензия 1C:Предприятие\n"
            f"<b>Сумма:</b> 85 500 ₽\n"
            f"<b>Взял в работу:</b> {user.display_name}\n"
            f"<b>Дата оплаты:</b> {scheduled_date}\n\n"
            f"Вы получите уведомление когда запрос будет оплачен."
        )

        await callback.message.answer(worker_text_date)

        # Пример уведомления о планировании на сегодня
        worker_text_today = (
            f"📅 <b>Запрос на оплату #125 запланирован на сегодня</b>\n\n"
            f"<b>Название:</b> Аренда офиса\n"
            f"<b>Сумма:</b> 150 000 ₽\n"
            f"<b>Взял в работу:</b> {user.display_name}\n\n"
            f"Вы получите уведомление когда запрос будет оплачен."
        )

        await callback.message.answer(worker_text_today)

    except Exception as e:
        logger.error(f"Error in test_worker_scheduled: {e}", exc_info=True)
        await callback.message.answer(f"❌ Ошибка: {e}")


@testing_router.callback_query(F.data == "test_worker_cancelled")
async def test_worker_cancelled(callback: CallbackQuery, user=None):
    """Тестовое уведомление сотруднику об отмене запроса"""
    if not user or user.role != UserRole.OWNER:
        await callback.answer("❌ Недостаточно прав", show_alert=True)
        return

    await callback.answer("⏳ Отправляю...")

    try:
        # Пример уведомления об отмене с причиной
        worker_text = (
            f"❌ <b>Запрос на оплату #126 отменён</b>\n\n"
            f"<b>Название:</b> Отменённый заказ оборудования\n"
            f"<b>Сумма:</b> 25 000 ₽\n"
            f"<b>Отменил:</b> {user.display_name}\n\n"
            f"<b>Причина отмены:</b>\n"
            f"Заказ отменён по причине изменения требований проекта."
        )

        await callback.message.answer(worker_text)

        # Пример автоматической отмены
        worker_text_auto = (
            f"❌ <b>Запрос на оплату #127 автоматически отменён</b>\n\n"
            f"<b>Название:</b> Просроченный платёж\n"
            f"<b>Сумма:</b> 10 000 ₽\n"
            f"<b>Взял в работу:</b> {user.display_name}\n\n"
            f"<b>Причина:</b> Запрос не был оплачен более 2 дней."
        )

        await callback.message.answer(worker_text_auto)

    except Exception as e:
        logger.error(f"Error in test_worker_cancelled: {e}", exc_info=True)
        await callback.message.answer(f"❌ Ошибка: {e}")


@testing_router.callback_query(F.data == "test_worker_overdue_reminder")
async def test_worker_overdue_reminder(callback: CallbackQuery, user=None):
    """Тестовое напоминание сотруднику о неоплаченном запросе"""
    if not user or user.role != UserRole.OWNER:
        await callback.answer("❌ Недостаточно прав", show_alert=True)
        return

    await callback.answer("⏳ Отправляю...")

    try:
        # Напоминание о неоплате SCHEDULED_TODAY (первый день)
        worker_text_first = (
            f"⚠️ <b>Запрос на оплату #128 не был оплачен вчера</b>\n\n"
            f"<b>Название:</b> Аренда офиса\n"
            f"<b>Сумма:</b> 150 000 ₽\n"
            f"<b>Взял в работу:</b> {user.display_name}\n\n"
            f"Запрос остается активным. Если не будет оплачен сегодня, "
            f"он будет автоматически отменён завтра в 10:00."
        )

        await callback.message.answer(worker_text_first)

        # Напоминание о просроченном SCHEDULED_DATE
        scheduled_date = (datetime.now() - timedelta(days=2)).strftime('%d.%m.%Y')
        worker_text_overdue = (
            f"⚠️ <b>Запрос на оплату #129 просрочен</b>\n\n"
            f"<b>Название:</b> Реклама Яндекс.Директ\n"
            f"<b>Сумма:</b> 50 000 ₽\n"
            f"<b>Был запланирован на:</b> {scheduled_date}\n\n"
            f"Запрос возвращён в статус ожидания."
        )

        await callback.message.answer(worker_text_overdue)

    except Exception as e:
        logger.error(f"Error in test_worker_overdue_reminder: {e}", exc_info=True)
        await callback.message.answer(f"❌ Ошибка: {e}")
