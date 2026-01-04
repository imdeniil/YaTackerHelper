"""Диалог создания запроса на оплату (Worker)"""

from aiogram_dialog import Dialog
from .windows import (
    title_window,
    amount_window,
    comment_window,
    attach_invoice_window,
    confirm_window,
    success_window,
)


payment_request_creation_dialog = Dialog(
    title_window,
    amount_window,
    comment_window,
    attach_invoice_window,
    confirm_window,
    success_window,
)


__all__ = ["payment_request_creation_dialog"]
