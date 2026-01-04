"""Data getters для диалога главного меню"""

from typing import Any
from aiogram_dialog import DialogManager

from bot.database import UserRole


async def get_main_menu_data(dialog_manager: DialogManager, **kwargs) -> dict[str, Any]:
    """Получает данные для главного меню"""
    user = kwargs.get("user")

    return {
        "is_owner": user.role == UserRole.OWNER if user else False,
        "is_manager_or_owner": user.role in [UserRole.OWNER, UserRole.MANAGER] if user else False,
        "is_billing_contact": user.is_billing_contact if user else False,
        "has_tracker_access": user.tracker_login is not None if user else False,
        "display_name": user.display_name if user else "Гость",
    }
