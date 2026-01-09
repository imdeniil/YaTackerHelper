"""Window definitions для диалога настроек пользователя"""

from aiogram_dialog import Window
from aiogram_dialog.widgets.text import Const, Format
from aiogram_dialog.widgets.kbd import Button, Cancel, ScrollingGroup, Select

from .states import UserSettings as UserSettingsState
from .getters import get_user_settings_data
from .handlers import (
    on_edit_queue,
    on_edit_portfolio,
    on_queue_selected,
    on_portfolio_selected,
    on_back_to_main,
)


user_settings_window = Window(
    # ===== Главный экран настроек (для менеджеров и владельцев) =====
    Format(
        "⚙️ <b>Настройки пользователя</b>\n\n"
        "📋 Очередь по умолчанию: <code>{default_queue}</code>\n"
        "📁 Портфель по умолчанию: <b>{default_portfolio_name}</b>",
        when=lambda data, widget, manager: data["step"] == "" and data.get("is_manager_or_owner", False),
    ),

    Button(
        Const("Изменить очередь"),
        id="edit_queue",
        on_click=on_edit_queue,
        when=lambda data, widget, manager: data["step"] == "" and data.get("is_manager_or_owner", False),
    ),
    Button(
        Const("Изменить портфель"),
        id="edit_portfolio",
        on_click=on_edit_portfolio,
        when=lambda data, widget, manager: data["step"] == "" and data.get("is_manager_or_owner", False),
    ),

    # ===== Главный экран настроек (для работников) =====
    Format(
        "⚙️ <b>Настройки пользователя</b>\n\n"
        "📋 Очередь по умолчанию: <code>{default_queue}</code>",
        when=lambda data, widget, manager: data["step"] == "" and not data.get("is_manager_or_owner", False),
    ),

    Button(
        Const("Изменить очередь"),
        id="edit_queue_worker",
        on_click=on_edit_queue,
        when=lambda data, widget, manager: data["step"] == "" and not data.get("is_manager_or_owner", False),
    ),

    # ===== Выбор очереди =====
    Const(
        "📋 <b>Выбор очереди по умолчанию</b>\n\nВыберите очередь из списка:",
        when=lambda data, widget, manager: data["step"] == "select_queue",
    ),

    ScrollingGroup(
        Select(
            Format("{item[name]} ({item[key]})"),
            id="queue_select",
            item_id_getter=lambda x: x["key"],
            items="queues",
            on_click=on_queue_selected,
        ),
        id="queues_scroll",
        width=1,
        height=5,
        when=lambda data, widget, manager: data["step"] == "select_queue",
    ),

    # ===== Выбор портфеля =====
    Const(
        "📁 <b>Выбор портфеля по умолчанию</b>\n\nВыберите портфель из списка:",
        when=lambda data, widget, manager: data["step"] == "select_portfolio",
    ),

    ScrollingGroup(
        Select(
            Format("{item[name]}"),
            id="portfolio_select",
            item_id_getter=lambda x: x["id"],
            items="portfolios",
            on_click=on_portfolio_selected,
        ),
        id="portfolios_scroll",
        width=1,
        height=5,
        when=lambda data, widget, manager: data["step"] == "select_portfolio",
    ),

    # Кнопка назад (при выборе)
    Button(
        Const("⬅️ Назад"),
        id="back",
        on_click=on_back_to_main,
        when=lambda data, widget, manager: data["step"] != "",
    ),

    # Выход в главное меню
    Cancel(Const("🏠 Главное меню")),

    state=UserSettingsState.main,
    getter=get_user_settings_data,
)
