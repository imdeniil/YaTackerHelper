"""Константы для диалога просмотра своих запросов на оплату"""

from bot.database import PaymentRequestStatus


STATUS_EMOJI = {
    PaymentRequestStatus.PENDING: "⏳",
    PaymentRequestStatus.SCHEDULED_TODAY: "📅",
    PaymentRequestStatus.SCHEDULED_DATE: "📅",
    PaymentRequestStatus.PAID: "✅",
    PaymentRequestStatus.CANCELLED: "❌",
}


def get_status_short(status: PaymentRequestStatus, scheduled_date=None) -> str:
    """Возвращает краткое описание статуса"""
    status_map = {
        PaymentRequestStatus.PENDING: "Ожидает",
        PaymentRequestStatus.SCHEDULED_TODAY: "Сегодня",
        PaymentRequestStatus.SCHEDULED_DATE: f"На {scheduled_date.strftime('%d.%m') if scheduled_date else '?'}",
        PaymentRequestStatus.PAID: "Оплачено",
        PaymentRequestStatus.CANCELLED: "Отменено",
    }
    return status_map.get(status, "?")


def get_status_text(status: PaymentRequestStatus, scheduled_date=None) -> str:
    """Возвращает полное описание статуса"""
    status_map = {
        PaymentRequestStatus.PENDING: "⏳ Ожидает оплаты",
        PaymentRequestStatus.SCHEDULED_TODAY: "📅 Оплатят сегодня",
        PaymentRequestStatus.SCHEDULED_DATE: f"📅 Запланировано на {scheduled_date.strftime('%d.%m.%Y') if scheduled_date else '?'}",
        PaymentRequestStatus.PAID: "✅ Оплачено",
        PaymentRequestStatus.CANCELLED: "❌ Отменено",
    }
    return status_map.get(status, "Неизвестно")
