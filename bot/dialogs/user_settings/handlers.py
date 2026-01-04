"""Handlers для диалога настроек пользователя"""

from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.kbd import Button, Select

from bot.database import get_session, UserCRUD


# ============ Edit Mode Handlers ============

async def on_edit_queue(callback: CallbackQuery, button: Button, manager: DialogManager):
    """Переключение в режим редактирования очереди"""
    manager.dialog_data["step"] = "select_queue"
    await manager.update({})


async def on_edit_portfolio(callback: CallbackQuery, button: Button, manager: DialogManager):
    """Переключение в режим редактирования портфеля"""
    manager.dialog_data["step"] = "select_portfolio"
    await manager.update({})


# ============ Selection Handlers ============

async def on_queue_selected(callback: CallbackQuery, widget: Select, manager: DialogManager, item_id: str):
    """Обработка выбора очереди"""
    user = manager.middleware_data.get("user")
    if not user:
        return

    async with get_session() as session:
        # Обновляем настройки в БД
        updated_settings = await UserCRUD.update_user_settings(session, user.id, default_queue=item_id)

        # Обновляем настройки в middleware_data для отображения
        if updated_settings:
            manager.middleware_data["user_settings"] = updated_settings

    # Возвращаемся к главному экрану без alert
    manager.dialog_data["step"] = ""
    await manager.update({})


async def on_portfolio_selected(callback: CallbackQuery, widget: Select, manager: DialogManager, item_id: str):
    """Обработка выбора портфеля"""
    user = manager.middleware_data.get("user")
    if not user:
        return

    async with get_session() as session:
        # Обновляем настройки в БД
        updated_settings = await UserCRUD.update_user_settings(session, user.id, default_portfolio=item_id)

        # Обновляем настройки в middleware_data для отображения
        if updated_settings:
            manager.middleware_data["user_settings"] = updated_settings

    # Возвращаемся к главному экрану без alert
    manager.dialog_data["step"] = ""
    await manager.update({})


# ============ Navigation Handlers ============

async def on_back_to_main(callback: CallbackQuery, button: Button, manager: DialogManager):
    """Возврат к главному экрану настроек"""
    manager.dialog_data["step"] = ""
    await manager.update({})
