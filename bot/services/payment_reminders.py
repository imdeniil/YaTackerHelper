"""Сервис напоминаний для запросов на оплату"""

import logging
from datetime import date, datetime
from aiogram import Bot

from bot.database import get_session, PaymentRequestCRUD, PaymentRequestStatus
from bot.handlers.payment_callbacks import format_payment_request_message, get_payment_request_keyboard

logger = logging.getLogger(__name__)


async def send_reminder_scheduled_today(bot: Bot):
    """Отправляет напоминания по запросам со статусом SCHEDULED_TODAY в 18:00 МСК

    Проверяет все запросы со статусом SCHEDULED_TODAY и отправляет напоминание
    billing контакту который взял запрос в работу.
    """
    logger.info("Running reminder check for SCHEDULED_TODAY payments...")

    async with get_session() as session:
        # Получаем все запросы со статусом SCHEDULED_TODAY
        requests = await PaymentRequestCRUD.get_all_payment_requests(
            session, status=PaymentRequestStatus.SCHEDULED_TODAY
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
            session, status=PaymentRequestStatus.SCHEDULED_DATE
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
    """Переносит неоплаченные SCHEDULED_TODAY на следующий день в 00:01 МСК

    Проверяет все запросы со статусом SCHEDULED_TODAY и если они не оплачены
    до полуночи, оставляет статус SCHEDULED_TODAY и уведомляет Worker и billing контакта.
    """
    logger.info("Running rollover check for SCHEDULED_TODAY payments...")

    async with get_session() as session:
        # Получаем все запросы со статусом SCHEDULED_TODAY
        requests = await PaymentRequestCRUD.get_all_payment_requests(
            session, status=PaymentRequestStatus.SCHEDULED_TODAY
        )

        if not requests:
            logger.info("No SCHEDULED_TODAY payments to rollover")
            return

        logger.info(f"Found {len(requests)} SCHEDULED_TODAY payment(s) to check for rollover")

        for payment_request in requests:
            try:
                # Уведомляем Worker о том что оплата не прошла
                if payment_request.created_by.telegram_id:
                    worker_text = (
                        f"⚠️ <b>Запрос на оплату #{payment_request.id} не был оплачен вчера</b>\n\n"
                        f"<b>Название:</b> {payment_request.title}\n"
                        f"<b>Сумма:</b> {payment_request.amount} ₽\n"
                        f"<b>Взял в работу:</b> {payment_request.processing_by.display_name if payment_request.processing_by else 'Не указан'}\n\n"
                        f"Запрос остается активным."
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
                        f"Пожалуйста, обновите статус запроса."
                    )

                    keyboard = get_payment_request_keyboard(payment_request.id, payment_request.status)

                    await bot.send_message(
                        chat_id=payment_request.processing_by.telegram_id,
                        text=billing_text,
                        reply_markup=keyboard,
                    )

                logger.info(f"Rollover notification sent for payment request #{payment_request.id}")

            except Exception as e:
                logger.error(
                    f"Error sending rollover notification for payment request #{payment_request.id}: {e}",
                    exc_info=True
                )
