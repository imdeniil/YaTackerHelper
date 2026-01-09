"""Сервис напоминаний для запросов на оплату"""

import logging
from datetime import date, datetime
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from bot.database import get_session, PaymentRequestCRUD, PaymentRequestStatus, UserCRUD
from bot.handlers.payments.callbacks import format_payment_request_message, get_payment_request_keyboard

logger = logging.getLogger(__name__)

# Количество платежей на странице в утренней рассылке
PENDING_PAGE_SIZE = 5

async def send_reminder_scheduled_today(bot: Bot):
    """Отправляет напоминания по запросам со статусом SCHEDULED_TODAY в 18:00 МСК

    Проверяет все запросы со статусом SCHEDULED_TODAY и отправляет напоминание
    billing контакту который взял запрос в работу.
    """
    logger.info("Running reminder check for SCHEDULED_TODAY payments...")

    async with get_session() as session:
        # Получаем все запросы со статусом SCHEDULED_TODAY
        requests = await PaymentRequestCRUD.get_all_payment_requests(
            session, status_filter=PaymentRequestStatus.SCHEDULED_TODAY.value, limit=0
        )

        if not requests:
            logger.info("No SCHEDULED_TODAY payments found")
            return

        logger.info(f"Found {len(requests)} SCHEDULED_TODAY payment(s)")

        for payment_request in requests:
            # Проверяем что есть processing_by (billing контакт)
            if not payment_request.processing_by or not payment_request.processing_by.telegram_id:
                logger.warning(f"Payment request #{payment_request.id} has no processing_by")
                continue

            try:
                # Формируем напоминание
                message_text = format_payment_request_message(
                    request_id=payment_request.id,
                    title=payment_request.title,
                    amount=payment_request.amount,
                    comment=payment_request.comment,
                    created_by_name=payment_request.created_by.display_name,
                    status=payment_request.status,
                    created_at=payment_request.created_at,
                    processing_by_name=payment_request.processing_by.display_name,
                )

                reminder_text = (
                    f"⏰ <b>Напоминание об оплате</b>\n\n"
                    f"{message_text}\n\n"
                    f"Вы планировали оплатить сегодня."
                )

                keyboard = get_payment_request_keyboard(payment_request.id, payment_request.status)

                # Отправляем напоминание
                await bot.send_message(
                    chat_id=payment_request.processing_by.telegram_id,
                    text=reminder_text,
                    reply_markup=keyboard,
                )

                logger.info(
                    f"Reminder sent to {payment_request.processing_by.telegram_username} "
                    f"for payment request #{payment_request.id}"
                )

            except Exception as e:
                logger.error(
                    f"Error sending reminder for payment request #{payment_request.id}: {e}",
                    exc_info=True
                )


async def send_reminder_scheduled_date(bot: Bot):
    """Отправляет напоминания по запросам со статусом SCHEDULED_DATE в 10:00 МСК

    Проверяет запросы со статусом SCHEDULED_DATE, запланированные на сегодня,
    и отправляет напоминание billing контакту.
    """
    logger.info("Running reminder check for SCHEDULED_DATE payments...")

    today = date.today()

    async with get_session() as session:
        # Получаем все запросы со статусом SCHEDULED_DATE
        all_scheduled = await PaymentRequestCRUD.get_all_payment_requests(
            session, status_filter=PaymentRequestStatus.SCHEDULED_DATE.value, limit=0
        )

        if not all_scheduled:
            logger.info("No SCHEDULED_DATE payments found")
            return

        # Фильтруем те, у которых scheduled_date == сегодня
        requests = [r for r in all_scheduled if r.scheduled_date == today]

        if not requests:
            logger.info(f"No SCHEDULED_DATE payments for today ({today})")
            return

        logger.info(f"Found {len(requests)} SCHEDULED_DATE payment(s) for today")

        for payment_request in requests:
            # Проверяем что есть processing_by (billing контакт)
            if not payment_request.processing_by or not payment_request.processing_by.telegram_id:
                logger.warning(f"Payment request #{payment_request.id} has no processing_by")
                continue

            try:
                # Формируем напоминание
                message_text = format_payment_request_message(
                    request_id=payment_request.id,
                    title=payment_request.title,
                    amount=payment_request.amount,
                    comment=payment_request.comment,
                    created_by_name=payment_request.created_by.display_name,
                    status=payment_request.status,
                    created_at=payment_request.created_at,
                    processing_by_name=payment_request.processing_by.display_name,
                    scheduled_date=payment_request.scheduled_date,
                )

                reminder_text = (
                    f"⏰ <b>Напоминание об оплате</b>\n\n"
                    f"{message_text}\n\n"
                    f"Сегодня запланирована оплата."
                )

                keyboard = get_payment_request_keyboard(payment_request.id, payment_request.status)

                # Отправляем напоминание
                await bot.send_message(
                    chat_id=payment_request.processing_by.telegram_id,
                    text=reminder_text,
                    reply_markup=keyboard,
                )

                logger.info(
                    f"Reminder sent to {payment_request.processing_by.telegram_username} "
                    f"for payment request #{payment_request.id}"
                )

            except Exception as e:
                logger.error(
                    f"Error sending reminder for payment request #{payment_request.id}: {e}",
                    exc_info=True
                )


async def rollover_scheduled_today(bot: Bot):
    """Проверяет неоплаченные SCHEDULED_TODAY в 10:00 МСК

    Проверяет все запросы со статусом SCHEDULED_TODAY:
    - Если запрос создан сегодня (первый день) - уведомляет Worker и billing
    - Если запрос создан вчера или раньше (второй день+) - АВТОМАТИЧЕСКИ ОТМЕНЯЕТ
    """
    logger.info("Running rollover check for SCHEDULED_TODAY payments...")

    today = date.today()

    async with get_session() as session:
        # Получаем все запросы со статусом SCHEDULED_TODAY
        requests = await PaymentRequestCRUD.get_all_payment_requests(
            session, status_filter=PaymentRequestStatus.SCHEDULED_TODAY.value, limit=0
        )

        if not requests:
            logger.info("No SCHEDULED_TODAY payments to rollover")
            return

        logger.info(f"Found {len(requests)} SCHEDULED_TODAY payment(s) to check for rollover")

        for payment_request in requests:
            try:
                # Проверяем дату создания запроса
                created_date = payment_request.created_at.date()

                # Если запрос НЕ создан сегодня (прошло >= 1 день) - ОТМЕНЯЕМ
                if created_date < today:
                    logger.info(
                        f"Auto-cancelling payment request #{payment_request.id} "
                        f"(created {created_date}, not paid for 2+ days)"
                    )

                    # Отменяем запрос
                    await PaymentRequestCRUD.cancel_payment_request(session, payment_request.id)

                    # Уведомляем Worker об автоматической отмене
                    if payment_request.created_by.telegram_id:
                        worker_text = (
                            f"❌ <b>Запрос на оплату #{payment_request.id} автоматически отменён</b>\n\n"
                            f"<b>Название:</b> {payment_request.title}\n"
                            f"<b>Сумма:</b> {payment_request.amount} ₽\n"
                            f"<b>Взял в работу:</b> {payment_request.processing_by.display_name if payment_request.processing_by else 'Не указан'}\n\n"
                            f"<b>Причина:</b> Запрос не был оплачен более 2 дней."
                        )

                        await bot.send_message(
                            chat_id=payment_request.created_by.telegram_id,
                            text=worker_text,
                        )

                    # Уведомляем billing контакт об автоматической отмене
                    if payment_request.processing_by and payment_request.processing_by.telegram_id:
                        billing_text = (
                            f"❌ <b>Запрос на оплату #{payment_request.id} автоматически отменён</b>\n\n"
                            f"<b>Название:</b> {payment_request.title}\n"
                            f"<b>Сумма:</b> {payment_request.amount} ₽\n\n"
                            f"<b>Причина:</b> Запрос не был оплачен более 2 дней."
                        )

                        await bot.send_message(
                            chat_id=payment_request.processing_by.telegram_id,
                            text=billing_text,
                        )

                    logger.info(f"Payment request #{payment_request.id} auto-cancelled")

                else:
                    # Запрос создан сегодня (первый день) - просто уведомляем
                    logger.info(
                        f"Sending reminder for payment request #{payment_request.id} "
                        f"(created today, first day)"
                    )

                    # Уведомляем Worker
                    if payment_request.created_by.telegram_id:
                        worker_text = (
                            f"⚠️ <b>Запрос на оплату #{payment_request.id} не был оплачен вчера</b>\n\n"
                            f"<b>Название:</b> {payment_request.title}\n"
                            f"<b>Сумма:</b> {payment_request.amount} ₽\n"
                            f"<b>Взял в работу:</b> {payment_request.processing_by.display_name if payment_request.processing_by else 'Не указан'}\n\n"
                            f"Запрос остается активным. Если не будет оплачен сегодня, он будет автоматически отменён завтра в 10:00."
                        )

                        await bot.send_message(
                            chat_id=payment_request.created_by.telegram_id,
                            text=worker_text,
                        )

                    # Уведомляем billing контакт
                    if payment_request.processing_by and payment_request.processing_by.telegram_id:
                        message_text = format_payment_request_message(
                            request_id=payment_request.id,
                            title=payment_request.title,
                            amount=payment_request.amount,
                            comment=payment_request.comment,
                            created_by_name=payment_request.created_by.display_name,
                            status=payment_request.status,
                            created_at=payment_request.created_at,
                            processing_by_name=payment_request.processing_by.display_name,
                        )

                        billing_text = (
                            f"⚠️ <b>Запрос на оплату #{payment_request.id} не был оплачен вчера</b>\n\n"
                            f"{message_text}\n\n"
                            f"Пожалуйста, оплатите сегодня или обновите статус. "
                            f"Запрос будет автоматически отменён завтра в 10:00 если не будет оплачен."
                        )

                        keyboard = get_payment_request_keyboard(payment_request.id, payment_request.status)

                        await bot.send_message(
                            chat_id=payment_request.processing_by.telegram_id,
                            text=billing_text,
                            reply_markup=keyboard,
                        )

                    logger.info(f"Rollover reminder sent for payment request #{payment_request.id}")

            except Exception as e:
                logger.error(
                    f"Error processing rollover for payment request #{payment_request.id}: {e}",
                    exc_info=True
                )


async def rollover_overdue_scheduled_date(bot: Bot):
    """Переводит просроченные SCHEDULED_DATE в PENDING в 10:00 МСК

    Если scheduled_date < сегодня, то статус меняется на PENDING,
    чтобы запрос снова появился в утреннем списке.
    """
    logger.info("Running rollover check for overdue SCHEDULED_DATE payments...")

    today = date.today()

    async with get_session() as session:
        # Получаем все запросы со статусом SCHEDULED_DATE
        all_scheduled = await PaymentRequestCRUD.get_all_payment_requests(
            session, status_filter=PaymentRequestStatus.SCHEDULED_DATE.value, limit=0
        )

        if not all_scheduled:
            logger.info("No SCHEDULED_DATE payments found")
            return

        # Фильтруем просроченные (scheduled_date < сегодня)
        overdue_requests = [r for r in all_scheduled if r.scheduled_date and r.scheduled_date < today]

        if not overdue_requests:
            logger.info("No overdue SCHEDULED_DATE payments found")
            return

        logger.info(f"Found {len(overdue_requests)} overdue SCHEDULED_DATE payment(s)")

        for payment_request in overdue_requests:
            try:
                # Переводим в статус PENDING
                await PaymentRequestCRUD.reset_to_pending(session, payment_request.id)

                logger.info(
                    f"Payment request #{payment_request.id} reset to PENDING "
                    f"(was scheduled for {payment_request.scheduled_date})"
                )

                # Уведомляем Worker о переносе
                if payment_request.created_by.telegram_id:
                    worker_text = (
                        f"⚠️ <b>Запрос на оплату #{payment_request.id} просрочен</b>\n\n"
                        f"<b>Название:</b> {payment_request.title}\n"
                        f"<b>Сумма:</b> {payment_request.amount} ₽\n"
                        f"<b>Был запланирован на:</b> {payment_request.scheduled_date.strftime('%d.%m.%Y')}\n\n"
                        f"Запрос возвращён в статус ожидания."
                    )

                    await bot.send_message(
                        chat_id=payment_request.created_by.telegram_id,
                        text=worker_text,
                    )

                # Уведомляем billing контакт (если был назначен)
                if payment_request.processing_by and payment_request.processing_by.telegram_id:
                    billing_text = (
                        f"⚠️ <b>Запрос на оплату #{payment_request.id} просрочен</b>\n\n"
                        f"<b>Название:</b> {payment_request.title}\n"
                        f"<b>Сумма:</b> {payment_request.amount} ₽\n"
                        f"<b>Был запланирован на:</b> {payment_request.scheduled_date.strftime('%d.%m.%Y')}\n\n"
                        f"Запрос возвращён в статус ожидания и появится в утреннем списке."
                    )

                    await bot.send_message(
                        chat_id=payment_request.processing_by.telegram_id,
                        text=billing_text,
                    )

            except Exception as e:
                logger.error(
                    f"Error resetting payment request #{payment_request.id} to PENDING: {e}",
                    exc_info=True
                )


def _build_pending_list_keyboard(
    requests: list,
    page: int,
    total_pages: int,
    billing_user_id: int
) -> InlineKeyboardMarkup:
    """Строит клавиатуру для списка PENDING платежей с пагинацией

    Args:
        requests: Список запросов на текущей странице
        page: Текущая страница (0-indexed)
        total_pages: Общее количество страниц
        billing_user_id: ID billing контакта для callback_data
    """
    buttons = []

    # Кнопки для каждого запроса
    for req in requests:
        title_short = req.title[:20] + "..." if len(req.title) > 20 else req.title
        buttons.append([
            InlineKeyboardButton(
                text=f"⏳ #{req.id} | {req.amount} ₽ | {title_short}",
                callback_data=f"pending_select:{req.id}"
            )
        ])

    # Пагинация
    nav_buttons = []
    if page > 0:
        nav_buttons.append(
            InlineKeyboardButton(text="◀️", callback_data=f"pending_page:{page - 1}")
        )
    nav_buttons.append(
        InlineKeyboardButton(text=f"{page + 1}/{total_pages}", callback_data="pending_noop")
    )
    if page < total_pages - 1:
        nav_buttons.append(
            InlineKeyboardButton(text="▶️", callback_data=f"pending_page:{page + 1}")
        )

    if nav_buttons:
        buttons.append(nav_buttons)

    return InlineKeyboardMarkup(inline_keyboard=buttons)


async def send_morning_pending_list(bot: Bot):
    """Отправляет утренний список PENDING платежей всем billing контактам в 09:00 МСК

    Каждый billing контакт получает список всех ожидающих платежей
    с возможностью выбрать и отреагировать на каждый.
    """
    logger.info("Running morning PENDING list distribution...")

    async with get_session() as session:
        # Получаем все PENDING запросы
        pending_requests = await PaymentRequestCRUD.get_all_payment_requests(
            session, status_filter=PaymentRequestStatus.PENDING.value, limit=0
        )

        if not pending_requests:
            logger.info("No PENDING payments for morning distribution")
            return

        logger.info(f"Found {len(pending_requests)} PENDING payment(s) for morning distribution")

        # Получаем всех billing контактов
        billing_contacts = await UserCRUD.get_billing_contacts(session)

        if not billing_contacts:
            logger.warning("No billing contacts found for morning distribution")
            return

        # Сортируем по дате создания (старые первые)
        pending_requests.sort(key=lambda x: x.created_at)

        total_amount = sum(
            float(req.amount.replace(" ", "").replace(",", "."))
            for req in pending_requests
            if req.amount
        )

        # Первая страница
        page = 0
        total_pages = (len(pending_requests) + PENDING_PAGE_SIZE - 1) // PENDING_PAGE_SIZE
        page_requests = pending_requests[:PENDING_PAGE_SIZE]

        # Формируем сообщение
        message_text = (
            f"🌅 <b>Доброе утро! Ожидающие платежи</b>\n\n"
            f"📊 Всего запросов: <b>{len(pending_requests)}</b>\n"
            f"💰 Общая сумма: <b>{total_amount:,.0f} ₽</b>\n\n"
            f"Выберите запрос для действия:"
        )

        # Отправляем каждому billing контакту
        for billing_contact in billing_contacts:
            if not billing_contact.telegram_id:
                continue

            try:
                keyboard = _build_pending_list_keyboard(
                    page_requests, page, total_pages, billing_contact.id
                )

                await bot.send_message(
                    chat_id=billing_contact.telegram_id,
                    text=message_text,
                    reply_markup=keyboard,
                )

                logger.info(f"Morning PENDING list sent to {billing_contact.telegram_username}")

            except Exception as e:
                logger.error(
                    f"Error sending morning PENDING list to {billing_contact.telegram_username}: {e}",
                    exc_info=True
                )
