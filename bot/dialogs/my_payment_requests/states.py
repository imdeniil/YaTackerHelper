"""Состояния для просмотра своих запросов на оплату."""

from aiogram.fsm.state import State, StatesGroup


class MyPaymentRequests(StatesGroup):
    """Состояния для просмотра своих запросов на оплату (Worker)."""

    list = State()
    view_details = State()
