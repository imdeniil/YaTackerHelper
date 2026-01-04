"""Диалог просмотра всех запросов на оплату (Billing контакты)"""

from aiogram_dialog import Dialog
from .windows import all_list_window, all_details_window, schedule_date_window


# Создаем диалог
all_payment_requests_dialog = Dialog(
    all_list_window,
    all_details_window,
    schedule_date_window,
)


__all__ = ["all_payment_requests_dialog"]
