"""Состояния для настроек пользователя."""

from aiogram.fsm.state import State, StatesGroup


class UserSettings(StatesGroup):
    """Состояния для настроек пользователя."""

    main = State()
