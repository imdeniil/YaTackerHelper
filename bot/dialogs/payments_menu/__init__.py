"""Диалог подменю платежей"""

from aiogram_dialog import Dialog
from .windows import payments_menu_window


payments_menu_dialog = Dialog(payments_menu_window)


__all__ = ["payments_menu_dialog"]
