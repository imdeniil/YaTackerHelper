"""Data getters для диалога создания платежа"""

from typing import Any
from aiogram_dialog import DialogManager

from bot.database.models import PaymentRequestStatus


async def get_title_data(dialog_manager: DialogManager, **kwargs) -> dict[str, Any]:
    """Данные для окна ввода названия"""
    return {
        "error": dialog_manager.dialog_data.get("error"),
    }


async def get_amount_data(dialog_manager: DialogManager, **kwargs) -> dict[str, Any]:
    """Данные для окна ввода суммы"""
    return {
        "title": dialog_manager.dialog_data.get("title", ""),
        "error": dialog_manager.dialog_data.get("error"),
    }


async def get_comment_data(dialog_manager: DialogManager, **kwargs) -> dict[str, Any]:
    """Данные для окна ввода комментария"""
    return {
        "title": dialog_manager.dialog_data.get("title", ""),
        "amount": dialog_manager.dialog_data.get("amount", ""),
        "error": dialog_manager.dialog_data.get("error"),
    }


async def get_status_data(dialog_manager: DialogManager, **kwargs) -> dict[str, Any]:
    """Данные для окна выбора статуса"""
    return {
        "title": dialog_manager.dialog_data.get("title", ""),
        "amount": dialog_manager.dialog_data.get("amount", ""),
        "comment": dialog_manager.dialog_data.get("comment", "—"),
    }


async def get_scheduled_date_data(dialog_manager: DialogManager, **kwargs) -> dict[str, Any]:
    """Данные для окна выбора даты планирования"""
    return {
        "title": dialog_manager.dialog_data.get("title", ""),
        "amount": dialog_manager.dialog_data.get("amount", ""),
        "error": dialog_manager.dialog_data.get("error"),
    }


async def get_paid_date_data(dialog_manager: DialogManager, **kwargs) -> dict[str, Any]:
    """Данные для окна выбора даты оплаты"""
    return {
        "title": dialog_manager.dialog_data.get("title", ""),
        "amount": dialog_manager.dialog_data.get("amount", ""),
        "error": dialog_manager.dialog_data.get("error"),
    }


async def get_invoice_data(dialog_manager: DialogManager, **kwargs) -> dict[str, Any]:
    """Данные для окна прикрепления счета"""
    return {
        "title": dialog_manager.dialog_data.get("title", ""),
        "amount": dialog_manager.dialog_data.get("amount", ""),
    }


async def get_payment_proof_data(dialog_manager: DialogManager, **kwargs) -> dict[str, Any]:
    """Данные для окна прикрепления платежки"""
    return {
        "title": dialog_manager.dialog_data.get("title", ""),
        "amount": dialog_manager.dialog_data.get("amount", ""),
        "paid_date": dialog_manager.dialog_data.get("paid_date", ""),
    }


async def get_confirm_data(dialog_manager: DialogManager, **kwargs) -> dict[str, Any]:
    """Данные для окна подтверждения"""
    status = dialog_manager.dialog_data.get("status", "pending")

    status_display = {
        "pending": "⏳ Ожидает оплаты",
        "scheduled": "📅 Запланирован",
        "paid": "✅ Оплачен",
    }.get(status, status)

    invoice_status = "📎 Прикреплен" if dialog_manager.dialog_data.get("invoice_file_id") else "—"
    payment_proof_status = "📎 Прикреплена" if dialog_manager.dialog_data.get("payment_proof_file_id") else "—"

    return {
        "title": dialog_manager.dialog_data.get("title", ""),
        "amount": dialog_manager.dialog_data.get("amount", ""),
        "comment": dialog_manager.dialog_data.get("comment", "—"),
        "status_display": status_display,
        "status": status,
        "scheduled_date": dialog_manager.dialog_data.get("scheduled_date", ""),
        "paid_date": dialog_manager.dialog_data.get("paid_date", ""),
        "invoice_status": invoice_status,
        "payment_proof_status": payment_proof_status,
        "is_scheduled": status == "scheduled",
        "is_paid": status == "paid",
    }


async def get_success_data(dialog_manager: DialogManager, **kwargs) -> dict[str, Any]:
    """Данные для окна успешного создания"""
    return {
        "payment_id": dialog_manager.dialog_data.get("payment_id", 0),
    }
