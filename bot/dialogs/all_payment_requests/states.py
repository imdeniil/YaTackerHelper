"""Состояния для просмотра всех запросов на оплату."""

from aiogram.fsm.state import State, StatesGroup


class AllPaymentRequests(StatesGroup):
    """Состояния для просмотра всех запросов на оплату (Billing)."""

    list = State()
    view_details = State()
    schedule_date = State()


class PaymentProcessing(StatesGroup):
    """Состояния для обработки оплаты (Billing)."""

    upload_proof = State()
    select_date = State()
