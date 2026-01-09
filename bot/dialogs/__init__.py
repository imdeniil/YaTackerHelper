"""Диалоги aiogram-dialog для бота."""

from .main_menu import main_menu_dialog
from .clone_project import clone_project_dialog
from .user_management import user_management_dialog
from .user_settings import user_settings_dialog
from .payment_request import payment_request_creation_dialog
from .my_payment_requests import my_payment_requests_dialog
from .all_payment_requests import all_payment_requests_dialog
from .payments_menu import payments_menu_dialog
from .create_payment import create_payment_dialog

__all__ = [
    "main_menu_dialog",
    "clone_project_dialog",
    "user_management_dialog",
    "user_settings_dialog",
    "payment_request_creation_dialog",
    "my_payment_requests_dialog",
    "all_payment_requests_dialog",
    "payments_menu_dialog",
    "create_payment_dialog",
]
