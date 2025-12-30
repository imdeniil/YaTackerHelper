"""Диалог главного меню."""

from typing import Any
from aiogram.types import CallbackQuery
from aiogram_dialog import Dialog, Window, DialogManager
from aiogram_dialog.widgets.kbd import Button, Column
from aiogram_dialog.widgets.text import Const, Format

from bot.states import MainMenu, CloneProject, ProjectInfo, UserManagement, UserSettings, PaymentRequestCreation, MyPaymentRequests, AllPaymentRequests
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


async def on_payment_request(
    callback: CallbackQuery, button: Button, manager: DialogManager
):
    """Обработчик нажатия на кнопку "Запросить оплату"."""
    await manager.start(PaymentRequestCreation.enter_title)


async def on_my_payment_requests(
    callback: CallbackQuery, button: Button, manager: DialogManager
):
    """Обработчик нажатия на кнопку "Мои запросы на оплату"."""
    await manager.start(MyPaymentRequests.list)


async def on_all_payment_requests(
    callback: CallbackQuery, button: Button, manager: DialogManager
):
    """Обработчик нажатия на кнопку "Все запросы на оплату"."""
    await manager.start(AllPaymentRequests.list)


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
                when=lambda data, widget, manager: data.get("is_manager_or_owner", False) and data.get("has_tracker_access", False),
            ),
            Button(
                Const("ℹ️ Информация о проекте"),
                id="project_info",
                on_click=on_project_info,
                when=lambda data, widget, manager: data.get("has_tracker_access", False),
            ),
            Button(
                Const("💰 Запросить оплату"),
                id="payment_request",
                on_click=on_payment_request,
                when=lambda data, widget, manager: not data.get("is_billing_contact", False),
            ),
            Button(
                Const("📝 Мои запросы на оплату"),
                id="my_payment_requests",
                on_click=on_my_payment_requests,
                when=lambda data, widget, manager: not data.get("is_billing_contact", False),
            ),
            Button(
                Const("📊 Все запросы на оплату"),
                id="all_payment_requests",
                on_click=on_all_payment_requests,
                when=lambda data, widget, manager: data.get("is_billing_contact", False),
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
