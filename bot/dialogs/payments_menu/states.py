"""Состояния для подменю платежей."""

from aiogram.fsm.state import State, StatesGroup


class PaymentsMenu(StatesGroup):
    """Подменю платежей."""

    main = State()
