"""Data getters для диалога управления пользователями"""

import logging
from typing import Any
from aiogram_dialog import DialogManager

from bot.database import get_session, UserCRUD, UserRole
from src.tracker_client import TrackerClient
from .constants import ROLE_MAPPING, ROLES_LIST, BILLING_CONTACT_OPTIONS

logger = logging.getLogger(__name__)


async def get_user_management_data(dialog_manager: DialogManager, **kwargs) -> dict[str, Any]:
    """Получает данные для окна управления пользователями"""
    mode = dialog_manager.dialog_data.get("mode", "list")
    step = dialog_manager.dialog_data.get("step", "")

    # Получаем список пользователей бота
    async with get_session() as session:
        users = await UserCRUD.get_all_users(session)

    # Текущий пользователь из middleware
    current_user = kwargs.get("event_from_user", {})
    user = kwargs.get("user")

    # Форматируем пользователей для отображения
    users_list = [
        {
            "id": str(u.id),
            "telegram_id": u.telegram_id,
            "username": u.telegram_username or "—",
            "tracker": u.tracker_login,
            "display_name": u.display_name,
            "role": u.role.value,
            "role_emoji": ROLE_MAPPING.get(u.role.value, {}).get("emoji", "❓"),
            "role_display": ROLE_MAPPING.get(u.role.value, {}).get("display", u.role.value),
            "is_billing_contact": u.is_billing_contact,
            "billing_emoji": "💳 " if u.is_billing_contact else "",
        }
        for u in users
    ]

    # Данные для создания/редактирования
    selected_user_id = dialog_manager.dialog_data.get("selected_user_id")
    new_user_data = dialog_manager.dialog_data.get("new_user_data", {})

    # Находим выбранного пользователя
    selected_user = None
    if selected_user_id:
        for u in users:
            if u.id == int(selected_user_id):
                selected_user = {
                    "id": str(u.id),
                    "telegram_id": u.telegram_id,
                    "username": u.telegram_username or "—",
                    "tracker": u.tracker_login,
                    "display_name": u.display_name,
                    "role": u.role.value,
                    "role_display": ROLE_MAPPING.get(u.role.value, {}).get("display", u.role.value),
                    "is_billing_contact": u.is_billing_contact,
                    "billing_status": "💳 Да" if u.is_billing_contact else "Нет",
                }
                break

    # Получаем список пользователей Tracker для выбора
    tracker_users = []
    tracker_users_map = {}  # Маппинг login -> display для сохранения display_name
    if step == "select_tracker_user" or (mode == "edit" and step == "tracker_login"):
        try:
            async with TrackerClient() as tracker:
                tracker_users_raw = await tracker.client.users.get()
                tracker_users = [
                    {
                        "login": u.get("login", ""),
                        "display": u.get("display", u.get("login", "")),
                    }
                    for u in tracker_users_raw
                    if not u.get("dismissed", False)  # Только активные
                ]
                # Создаем маппинг для быстрого доступа
                tracker_users_map = {
                    u["login"]: u["display"] for u in tracker_users
                }
                logger.info(f"Loaded {len(tracker_users)} active tracker users")
        except Exception as e:
            logger.error(f"Error fetching tracker users: {e}", exc_info=True)

    # Сохраняем tracker_users_map в dialog_data для использования в обработчиках
    if tracker_users_map:
        dialog_manager.dialog_data["tracker_users_map"] = tracker_users_map

    # Подготавливаем tracker_login для отображения
    tracker_login_display = new_user_data.get("tracker_login", "Не указан")
    if tracker_login_display is None:
        tracker_login_display = "Не указан"

    # Подготавливаем роль для отображения по-русски
    role_display_ru = ""
    if "role" in new_user_data:
        role_display_ru = ROLE_MAPPING.get(new_user_data["role"], {}).get("display", new_user_data["role"])

    return {
        "mode": mode,
        "step": step,
        "users": users_list,
        "users_count": len(users_list),
        "current_user_role": user.role.value if user else "worker",
        "is_owner": user.role == UserRole.OWNER if user else False,
        "selected_user": selected_user,
        "new_user_data": new_user_data,
        "tracker_login_display": tracker_login_display,
        "role_display_ru": role_display_ru,
        "tracker_users": tracker_users,
        "roles": ROLES_LIST,
        "billing_contact_options": BILLING_CONTACT_OPTIONS,
        "error": dialog_manager.dialog_data.get("error"),
    }
