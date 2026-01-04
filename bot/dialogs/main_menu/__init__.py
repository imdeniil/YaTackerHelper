"""Диалог главного меню"""

from aiogram_dialog import Dialog
from .windows import main_menu_window


main_menu_dialog = Dialog(main_menu_window)


__all__ = ["main_menu_dialog"]
