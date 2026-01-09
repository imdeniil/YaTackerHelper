"""Состояния для создания платежа."""

from aiogram.fsm.state import State, StatesGroup


class CreatePayment(StatesGroup):
    """Состояния для создания платежа (Owner/Manager)."""

    enter_title = State()
    enter_amount = State()
    enter_comment = State()
    select_status = State()
    enter_scheduled_date = State()
    enter_paid_date = State()
    attach_invoice = State()
    attach_payment_proof = State()
    confirm = State()
    success = State()
