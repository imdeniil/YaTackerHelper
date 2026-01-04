"""Диалог для клонирования проекта"""

from aiogram_dialog import Dialog
from .windows import (
    select_project_window,
    confirm_project_window,
    enter_new_name_window,
    enter_queue_window,
    confirm_clone_window,
)


clone_project_dialog = Dialog(
    select_project_window,
    confirm_project_window,
    enter_new_name_window,
    enter_queue_window,
    confirm_clone_window,
)


__all__ = ["clone_project_dialog"]
