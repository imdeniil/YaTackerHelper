"""Data getters для диалога подменю платежей"""

from typing import Any
from aiogram_dialog import DialogManager

from bot.database.models import UserRole


async def get_payments_menu_data(dialog_manager: DialogManager, **kwargs) -> dict[str, Any]:
    """Получает данные для подменю платежей"""
    user = kwargs.get("user")

    is_owner = user.role == UserRole.OWNER if user else False
    is_manager = user.role == UserRole.MANAGER if user else False
    is_billing_contact = user.is_billing_contact if user else False

    return {
        "display_name": user.display_name if user else "Пользователь",
        "is_owner": is_owner,
        "is_manager": is_manager,
        "is_manager_or_owner": is_manager or is_owner,
        "is_billing_contact": is_billing_contact,
        # Показываем "Добавить платёж" для владельцев/менеджеров (как в вебе)
        "can_create_payment": is_owner or is_manager,
    }
