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


class PaymentRequestCreation(StatesGroup):
    """Состояния для создания запроса на оплату (Worker)."""

    enter_title = State()  # Ввод названия для плательщика
    enter_amount = State()  # Ввод суммы
    enter_comment = State()  # Ввод комментария
    attach_invoice = State()  # Прикрепление счета (опционально)
    confirm = State()  # Подтверждение запроса
    success = State()  # Успешное создание запроса


class MyPaymentRequests(StatesGroup):
    """Состояния для просмотра своих запросов на оплату (Worker)."""

    list = State()  # Список запросов
    view_details = State()  # Детали конкретного запроса


class AllPaymentRequests(StatesGroup):
    """Состояния для просмотра всех запросов на оплату (Billing)."""

    list = State()  # Список запросов
    view_details = State()  # Детали конкретного запроса
    schedule_date = State()  # Выбор даты для планирования оплаты


class PaymentProcessing(StatesGroup):
    """Состояния для обработки оплаты (Billing)."""

    upload_proof = State()  # Загрузка платежки для оплаченного запроса
    select_date = State()  # Выбор даты для планирования оплаты
