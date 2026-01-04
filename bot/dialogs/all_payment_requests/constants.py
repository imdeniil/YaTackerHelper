"""Константы для диалога просмотра всех запросов на оплату"""

from bot.database import PaymentRequestStatus


# Эмодзи статусов
STATUS_EMOJI = {
    PaymentRequestStatus.PENDING: "⏳",
    PaymentRequestStatus.SCHEDULED_TODAY: "📅",
    PaymentRequestStatus.SCHEDULED_DATE: "📅",
    PaymentRequestStatus.PAID: "✅",
    PaymentRequestStatus.CANCELLED: "❌",
}


# Краткие описания статусов (для списка)
def get_status_short(status: PaymentRequestStatus, scheduled_date=None) -> str:
    """Возвращает краткое описание статуса"""
    if status == PaymentRequestStatus.PENDING:
        return "Ожидает"
    elif status == PaymentRequestStatus.SCHEDULED_TODAY:
        return "Сегодня"
    elif status == PaymentRequestStatus.SCHEDULED_DATE:
        if scheduled_date:
            return f"На {scheduled_date.strftime('%d.%m')}"
        return "Запланировано"
    elif status == PaymentRequestStatus.PAID:
        return "Оплачено"
    elif status == PaymentRequestStatus.CANCELLED:
        return "Отменено"
    else:
        return "?"


# Полные описания статусов (для деталей)
def get_status_text(status: PaymentRequestStatus, scheduled_date=None) -> str:
    """Возвращает полное описание статуса"""
    if status == PaymentRequestStatus.PENDING:
        return "⏳ Ожидает оплаты"
    elif status == PaymentRequestStatus.SCHEDULED_TODAY:
        return "📅 Оплачу сегодня"
    elif status == PaymentRequestStatus.SCHEDULED_DATE:
        if scheduled_date:
            return f"📅 Запланировано на {scheduled_date.strftime('%d.%m.%Y')}"
        return "📅 Запланировано"
    elif status == PaymentRequestStatus.PAID:
        return "✅ Оплачено"
    elif status == PaymentRequestStatus.CANCELLED:
        return "❌ Отменено"
    else:
        return "Неизвестно"
