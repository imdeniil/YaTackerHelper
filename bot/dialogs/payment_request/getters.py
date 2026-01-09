"""Data getters для диалога создания запроса на оплату"""

from typing import Any
from aiogram_dialog import DialogManager

from bot.database import get_session, PaymentRequestCRUD
from bot.handlers.payments.callbacks import format_payment_request_message


async def get_title_data(dialog_manager: DialogManager, **kwargs) -> dict[str, Any]:
    """Получает данные для окна ввода названия"""
    return {
        "error": dialog_manager.dialog_data.get("error"),
    }


async def get_amount_data(dialog_manager: DialogManager, **kwargs) -> dict[str, Any]:
    """Получает данные для окна ввода суммы"""
    title = dialog_manager.dialog_data.get("title", "")
    return {
        "title": title,
        "error": dialog_manager.dialog_data.get("error"),
    }


async def get_comment_data(dialog_manager: DialogManager, **kwargs) -> dict[str, Any]:
    """Получает данные для окна ввода комментария"""
    title = dialog_manager.dialog_data.get("title", "")
    amount = dialog_manager.dialog_data.get("amount", "")
    return {
        "title": title,
        "amount": amount,
        "error": dialog_manager.dialog_data.get("error"),
    }


async def get_attach_invoice_data(dialog_manager: DialogManager, **kwargs) -> dict[str, Any]:
    """Получает данные для окна прикрепления счета"""
    title = dialog_manager.dialog_data.get("title", "")
    amount = dialog_manager.dialog_data.get("amount", "")
    comment = dialog_manager.dialog_data.get("comment", "")
    return {
        "title": title,
        "amount": amount,
        "comment": comment,
    }


async def get_confirm_data(dialog_manager: DialogManager, **kwargs) -> dict[str, Any]:
    """Получает данные для окна подтверждения"""
    title = dialog_manager.dialog_data.get("title", "")
    amount = dialog_manager.dialog_data.get("amount", "")
    comment = dialog_manager.dialog_data.get("comment", "")
    invoice_file_id = dialog_manager.dialog_data.get("invoice_file_id")

    return {
        "title": title,
        "amount": amount,
        "comment": comment,
        "invoice_status": "✅ Прикреплен" if invoice_file_id else "❌ Не прикреплен",
    }


async def get_success_data(dialog_manager: DialogManager, **kwargs) -> dict[str, Any]:
    """Получает данные для окна успешного создания"""
    user = kwargs.get("user")
    payment_request_id = dialog_manager.dialog_data.get("payment_request_id")
    billing_contacts_count = dialog_manager.dialog_data.get("billing_contacts_count", 0)

    async with get_session() as session:
        payment_request = await PaymentRequestCRUD.get_payment_request_by_id(session, payment_request_id)

        if not payment_request:
            return {"error": "Request not found"}

        # Форматируем полное сообщение о запросе
        request_text = format_payment_request_message(
            request_id=payment_request.id,
            title=payment_request.title,
            amount=payment_request.amount,
            comment=payment_request.comment,
            created_by_name=user.display_name,
            status=payment_request.status,
            created_at=payment_request.created_at,
        )

        return {
            "request_text": request_text,
            "billing_contacts_count": billing_contacts_count,
        }
