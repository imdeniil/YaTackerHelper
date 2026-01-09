"""Диалог создания платежа (Owner/Manager)"""

from aiogram_dialog import Dialog
from .windows import (
    title_window,
    amount_window,
    comment_window,
    status_window,
    scheduled_date_window,
    paid_date_window,
    invoice_window,
    payment_proof_window,
    confirm_window,
    success_window,
)


create_payment_dialog = Dialog(
    title_window,
    amount_window,
    comment_window,
    status_window,
    scheduled_date_window,
    paid_date_window,
    invoice_window,
    payment_proof_window,
    confirm_window,
    success_window,
)


__all__ = ["create_payment_dialog"]
