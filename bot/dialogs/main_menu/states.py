"""Состояния для главного меню."""

from aiogram.fsm.state import State, StatesGroup


class MainMenu(StatesGroup):
    """Главное меню бота."""

    main = State()
