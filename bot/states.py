"""Состояния бота для клонирования проектов."""

from aiogram.fsm.state import State, StatesGroup


class MainMenu(StatesGroup):
    """Главное меню бота."""

    main = State()


class CloneProject(StatesGroup):
    """Состояния для процесса клонирования проекта."""

    select_project = State()  # Выбор проекта для клонирования
    confirm_project = State()  # Подтверждение выбранного проекта
    enter_new_name = State()  # Ввод имени нового проекта
    enter_queue = State()  # Ввод целевой очереди
    confirm_clone = State()  # Финальное подтверждение (динамическое окно: подтверждение/прогресс/результат)


class ProjectInfo(StatesGroup):
    """Состояния для просмотра информации о проекте."""

    select_project = State()  # Выбор проекта
    show_info = State()  # Показ информации о проекте


class UserManagement(StatesGroup):
    """Состояния для управления пользователями (CRUD)."""

    main = State()  # Главное окно управления пользователями


class UserSettings(StatesGroup):
    """Состояния для настроек пользователя."""

    main = State()  # Главное окно настроек
