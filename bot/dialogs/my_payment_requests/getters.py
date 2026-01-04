"""Data getters для диалога просмотра своих запросов на оплату"""

from typing import Any
from aiogram_dialog import DialogManager

from bot.database import get_session, PaymentRequestCRUD, PaymentRequestStatus
from .constants import STATUS_EMOJI, get_status_short, get_status_text


async def get_my_requests_list_data(dialog_manager: DialogManager, **kwargs) -> dict[str, Any]:
    """Получает список запросов на оплату пользователя"""
    user = kwargs.get("user")
    if not user:
        return {"requests": [], "count": 0}

    # Получаем фильтр из dialog_data (по умолчанию - активные)
    status_filter = dialog_manager.dialog_data.get("status_filter", "active")

    async with get_session() as session:
        # Получаем все запросы пользователя
        all_requests = await PaymentRequestCRUD.get_user_payment_requests(session, user.id)

        # Применяем фильтр
        if status_filter == "active":
            # Активные: все кроме PAID и CANCELLED
            requests = [
                r for r in all_requests
                if r.status not in [PaymentRequestStatus.PAID, PaymentRequestStatus.CANCELLED]
            ]
        elif status_filter == "completed":
            # Завершенные: только PAID
            requests = [r for r in all_requests if r.status == PaymentRequestStatus.PAID]
        elif status_filter == "cancelled":
            # Отмененные: только CANCELLED
            requests = [r for r in all_requests if r.status == PaymentRequestStatus.CANCELLED]
        else:
            # На случай старых фильтров - показываем активные
            requests = [
                r for r in all_requests
                if r.status not in [PaymentRequestStatus.PAID, PaymentRequestStatus.CANCELLED]
            ]

        # Форматируем для отображения
        formatted_requests = []
        for req in requests:
            formatted_requests.append({
                "id": req.id,
                "title": req.title[:30] + "..." if len(req.title) > 30 else req.title,
                "amount": req.amount,
                "status_emoji": STATUS_EMOJI.get(req.status, "❓"),
                "status_text": get_status_short(req.status, req.scheduled_date),
                "created_at": req.created_at.strftime("%d.%m.%Y"),
            })

    return {
        "requests": formatted_requests,
        "count": len(formatted_requests),
        "total_count": len(all_requests),
        "current_filter": status_filter,
    }


async def get_request_details_data(dialog_manager: DialogManager, **kwargs) -> dict[str, Any]:
    """Получает детали конкретного запроса"""
    request_id = dialog_manager.dialog_data.get("selected_request_id")

    if not request_id:
        return {"error": "Request ID not found"}

    async with get_session() as session:
        payment_request = await PaymentRequestCRUD.get_payment_request_by_id(session, request_id)

        if not payment_request:
            return {"error": "Request not found"}

        return {
            "id": payment_request.id,
            "title": payment_request.title,
            "amount": payment_request.amount,
            "comment": payment_request.comment,
            "status": get_status_text(payment_request.status, payment_request.scheduled_date),
            "created_at": payment_request.created_at.strftime("%d.%m.%Y %H:%M"),
            "has_invoice": payment_request.invoice_file_id is not None,
            "invoice_file_id": payment_request.invoice_file_id,
            "invoice_status": "Прикреплен" if payment_request.invoice_file_id else "Не прикреплен",
            "processing_by": payment_request.processing_by.display_name if payment_request.processing_by else None,
            "paid_by": payment_request.paid_by.display_name if payment_request.paid_by else None,
            "paid_at": payment_request.paid_at.strftime("%d.%m.%Y %H:%M") if payment_request.paid_at else None,
            "has_payment_proof": payment_request.payment_proof_file_id is not None,
            "payment_proof_file_id": payment_request.payment_proof_file_id,
            "payment_proof_status": "Прикреплена" if payment_request.payment_proof_file_id else "Не прикреплена",
            "can_cancel": payment_request.status == PaymentRequestStatus.PENDING,
            "status_raw": payment_request.status,
        }
