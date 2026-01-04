"""Диалог просмотра своих запросов на оплату (Worker)"""

from aiogram_dialog import Dialog
from .windows import list_window, details_window


my_payment_requests_dialog = Dialog(
    list_window,
    details_window,
)


__all__ = ["my_payment_requests_dialog"]
