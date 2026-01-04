"""Window definitions для диалога главного меню"""

from aiogram_dialog import Window
from aiogram_dialog.widgets.kbd import Button, Column
from aiogram_dialog.widgets.text import Const, Format

from bot.states import MainMenu
from .getters import get_main_menu_data
from .handlers import (
    on_clone_project,
    on_project_info,
    on_user_management,
    on_user_settings,
    on_payment_request,
    on_my_payment_requests,
    on_all_payment_requests,
)


main_menu_window = Window(
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
)
