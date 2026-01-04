"""Handlers для диалога главного меню"""

from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.kbd import Button

from bot.states import (
    CloneProject,
    ProjectInfo,
    UserManagement,
    UserSettings,
    PaymentRequestCreation,
    MyPaymentRequests,
    AllPaymentRequests,
)


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
