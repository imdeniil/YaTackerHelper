"""Состояния для управления пользователями."""

from aiogram.fsm.state import State, StatesGroup


class UserManagement(StatesGroup):
    """Состояния для управления пользователями (CRUD)."""

    main = State()
