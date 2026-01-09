"""Window definitions для диалога подменю платежей"""

from aiogram_dialog import Window
from aiogram_dialog.widgets.kbd import Button, Column
from aiogram_dialog.widgets.text import Const, Format

from .states import PaymentsMenu
from .getters import get_payments_menu_data
from .handlers import on_all_payments, on_create_payment, on_back_to_main


payments_menu_window = Window(
    Format("💳 Платежи\n"),
    Const("Выберите действие:"),
    Column(
        Button(
            Const("📊 Все платежи"),
            id="all_payments",
            on_click=on_all_payments,
        ),
        Button(
            Const("➕ Добавить платёж"),
            id="create_payment",
            on_click=on_create_payment,
            when=lambda data, widget, manager: data.get("can_create_payment", False),
        ),
        Button(
            Const("◀️ Назад"),
            id="back_to_main",
            on_click=on_back_to_main,
        ),
    ),
    state=PaymentsMenu.main,
    getter=get_payments_menu_data,
)
