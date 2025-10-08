"""Диалог главного меню."""

from typing import Any
from aiogram.types import CallbackQuery
from aiogram_dialog import Dialog, Window, DialogManager
from aiogram_dialog.widgets.kbd import Button, Column
from aiogram_dialog.widgets.text import Const, Format

from bot.states import MainMenu, CloneProject, ProjectInfo, UserManagement, UserSettings
from bot.database import UserRole


async def on_clone_project(
    callback: CallbackQuery, button: Button, manager: DialogManager
):
    """
    Обработчик нажатия на кнопку "Клонировать проект".

    Args:
        callback: Callback от кнопки
        button: Кнопка которая была нажата
        manager: Менеджер диалогов
    """
    await manager.start(CloneProject.select_project)


async def on_project_info(
    callback: CallbackQuery, button: Button, manager: DialogManager
):
    """
    Обработчик нажатия на кнопку "Информация о проекте".

    Args:
        callback: Callback от кнопки
        button: Кнопка которая была нажата
        manager: Менеджер диалогов
    """
    await manager.start(ProjectInfo.select_project)


async def on_user_management(
    callback: CallbackQuery, button: Button, manager: DialogManager
):
    """Обработчик нажатия на кнопку "Управление пользователями"."""
    await manager.start(UserManagement.main)


async def on_user_settings(
    callback: CallbackQuery, button: Button, manager: DialogManager
):
    """Обработчик нажатия на кнопку "Настройки"."""
    await manager.start(UserSettings.main)


async def get_main_menu_data(dialog_manager: DialogManager, **kwargs) -> dict[str, Any]:
    """Получает данные для главного меню"""
    user = kwargs.get("user")

    return {
        "is_owner": user.role == UserRole.OWNER if user else False,
        "is_manager_or_owner": user.role in [UserRole.OWNER, UserRole.MANAGER] if user else False,
        "display_name": user.display_name if user else "Гость",
    }


# Главное меню
main_menu_dialog = Dialog(
    Window(
        Format("Привет, {display_name}\n"),
        Const("Выберите действие:"),
        Column(
            Button(
                Const("📋 Клонировать проект"),
                id="clone_project",
                on_click=on_clone_project,
                when=lambda data, widget, manager: data.get("is_manager_or_owner", False),
            ),
            Button(
                Const("👥 Управление пользователями"),
                id="user_management",
                on_click=on_user_management,
                when=lambda data, widget, manager: data.get("is_owner", False),
            ),
            Button(
                Const("⚙️ Настройки"),
                id="user_settings",
                on_click=on_user_settings,
                when=lambda data, widget, manager: data.get("is_manager_or_owner", False),
            ),
        ),
        state=MainMenu.main,
        getter=get_main_menu_data,
    ),
)
