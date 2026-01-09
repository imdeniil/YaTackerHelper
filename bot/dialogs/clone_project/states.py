"""Состояния для клонирования проекта."""

from aiogram.fsm.state import State, StatesGroup


class CloneProject(StatesGroup):
    """Состояния для процесса клонирования проекта."""

    select_project = State()
    confirm_project = State()
    enter_new_name = State()
    enter_queue = State()
    confirm_clone = State()


class ProjectInfo(StatesGroup):
    """Состояния для просмотра информации о проекте."""

    select_project = State()
    show_info = State()
