"""Состояния для создания запроса на оплату."""

from aiogram.fsm.state import State, StatesGroup


class PaymentRequestCreation(StatesGroup):
    """Состояния для создания запроса на оплату (Worker)."""

    enter_title = State()
    enter_amount = State()
    enter_comment = State()
    attach_invoice = State()
    confirm = State()
    success = State()
