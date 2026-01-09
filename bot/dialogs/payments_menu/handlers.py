"""Handlers для диалога подменю платежей"""

from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.kbd import Button

from bot.dialogs.all_payment_requests.states import AllPaymentRequests
from bot.dialogs.create_payment.states import CreatePayment


async def on_all_payments(
    callback: CallbackQuery, button: Button, manager: DialogManager
):
    """Обработчик нажатия на кнопку 'Все платежи'."""
    await manager.start(AllPaymentRequests.list)


async def on_create_payment(
    callback: CallbackQuery, button: Button, manager: DialogManager
):
    """Обработчик нажатия на кнопку 'Добавить платёж'."""
    await manager.start(CreatePayment.enter_title)


async def on_back_to_main(
    callback: CallbackQuery, button: Button, manager: DialogManager
):
    """Обработчик нажатия на кнопку 'Назад'."""
    await manager.done()
