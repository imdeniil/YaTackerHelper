"""Handlers для диалога главного меню"""

from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.kbd import Button

from bot.dialogs.clone_project.states import CloneProject, ProjectInfo
from bot.dialogs.user_management.states import UserManagement
from bot.dialogs.user_settings.states import UserSettings
from bot.dialogs.payment_request.states import PaymentRequestCreation
from bot.dialogs.my_payment_requests.states import MyPaymentRequests
from bot.dialogs.all_payment_requests.states import AllPaymentRequests
from bot.dialogs.payments_menu.states import PaymentsMenu


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


async def on_payments_menu(
    callback: CallbackQuery, button: Button, manager: DialogManager
):
    """Обработчик нажатия на кнопку "Платежи" (подменю)."""
    await manager.start(PaymentsMenu.main)
