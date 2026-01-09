"""Вспомогательные функции для маршрутов"""

import logging
from bot.database.models import PaymentRequestStatus
from bot.database.crud import BillingNotificationCRUD
from web.database import UserCRUD
from web.telegram_utils import send_telegram_message, send_telegram_document

logger = logging.getLogger(__name__)


def format_payment_request_message(payment_request, created_by_name: str) -> str:
    """Форматирует сообщение для billing контактов (аналогично боту)"""
    status_emoji = {
        PaymentRequestStatus.PENDING: "⏳",
        PaymentRequestStatus.SCHEDULED_TODAY: "📅",
        PaymentRequestStatus.SCHEDULED_DATE: "📅",
        PaymentRequestStatus.PAID: "✅",
        PaymentRequestStatus.CANCELLED: "❌",
    }

    status_text = {
        PaymentRequestStatus.PENDING: "Ожидает оплаты",
        PaymentRequestStatus.SCHEDULED_TODAY: "Оплачу сегодня",
        PaymentRequestStatus.SCHEDULED_DATE: f"Запланировано",
        PaymentRequestStatus.PAID: "Оплачено",
        PaymentRequestStatus.CANCELLED: "Отменено",
    }

    message = (
        f"{status_emoji.get(payment_request.status, '❓')} <b>Запрос на оплату #{payment_request.id}</b>\n\n"
        f"<b>Статус:</b> {status_text.get(payment_request.status, 'Неизвестно')}\n"
        f"<b>Название:</b> {payment_request.title}\n"
        f"<b>Сумма:</b> {payment_request.amount} ₽\n"
        f"<b>Комментарий:</b> {payment_request.comment}\n\n"
        f"<b>Создал:</b> {created_by_name}\n"
        f"<b>Дата создания:</b> {payment_request.created_at.strftime('%d.%m.%Y %H:%M')}\n"
    )

    return message


def get_payment_keyboard(request_id: int) -> dict:
    """Возвращает inline клавиатуру для запроса на оплату"""
    return {
        "inline_keyboard": [
            [{"text": "✅ Оплачено", "callback_data": f"pay_paid:{request_id}"}],
            [{"text": "📅 Запланировать", "callback_data": f"pay_schedule:{request_id}"}],
            [{"text": "❌ Отменить", "callback_data": f"pay_cancel:{request_id}"}],
        ]
    }


async def notify_billing_contacts_about_new_payment(
    session,
    config,
    payment_request,
    user,
    invoice_file_id: str = None
):
    """Отправляет уведомления всем billing контактам о новом запросе на оплату

    Args:
        session: Сессия БД
        config: Конфигурация (содержит bot_token)
        payment_request: Созданный запрос на оплату
        user: Пользователь-создатель
        invoice_file_id: ID файла счета (опционально)
    """
    # Получаем billing контакты
    billing_contacts = await UserCRUD.get_billing_contacts(session)

    if not billing_contacts:
        logger.warning("No billing contacts found for payment notification!")
        return

    # Формируем сообщение
    message_text = format_payment_request_message(payment_request, user.display_name)
    keyboard = get_payment_keyboard(payment_request.id)

    # Отправляем уведомление ВСЕМ billing контактам
    for billing_contact in billing_contacts:
        if billing_contact.telegram_id:
            try:
                # Отправляем сообщение
                message_id = await send_telegram_message(
                    bot_token=config.bot_token,
                    chat_id=billing_contact.telegram_id,
                    text=message_text,
                    reply_markup=keyboard
                )

                if message_id:
                    # Сохраняем уведомление в базу
                    await BillingNotificationCRUD.create_billing_notification(
                        session=session,
                        payment_request_id=payment_request.id,
                        billing_user_id=billing_contact.id,
                        message_id=message_id,
                        chat_id=billing_contact.telegram_id,
                    )

                    logger.info(f"Notification sent to billing contact {billing_contact.telegram_username}")

                    # Если есть счет, отправляем его отдельным документом
                    if invoice_file_id:
                        await send_telegram_document(
                            bot_token=config.bot_token,
                            chat_id=billing_contact.telegram_id,
                            document_file_id=invoice_file_id,
                            caption=f"📎 Счет к запросу #{payment_request.id}"
                        )

            except Exception as e:
                logger.error(f"Error sending notification to {billing_contact.telegram_username}: {e}")
