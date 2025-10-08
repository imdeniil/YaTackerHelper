"""Диалоги aiogram-dialog для бота."""

from .main_menu import main_menu_dialog
from .clone_project import clone_project_dialog
from .project_info import project_info_dialog
from .user_management import user_management_dialog
from .user_settings import user_settings_dialog

__all__ = [
    "main_menu_dialog",
    "clone_project_dialog",
    "project_info_dialog",
    "user_management_dialog",
    "user_settings_dialog",
]
