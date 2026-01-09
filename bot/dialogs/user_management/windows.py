"""Window definitions для диалога управления пользователями"""

from aiogram_dialog import Window
from aiogram_dialog.widgets.text import Const, Format
from aiogram_dialog.widgets.kbd import Button, ScrollingGroup, Select, Cancel
from aiogram_dialog.widgets.input import MessageInput

from .states import UserManagement
from .getters import get_user_management_data
from .handlers import (
    on_switch_to_create,
    on_switch_to_list,
    on_user_selected,
    on_delete_user_confirm,
    on_switch_to_delete,
    on_tracker_user_selected,
    on_skip_tracker,
    on_role_selected,
    on_billing_contact_selected,
    on_edit_field,
    on_edit_role_selected,
    on_edit_tracker_user_selected,
    on_back_from_edit_step,
    on_toggle_billing_contact,
    on_text_input,
)


user_management_window = Window(
    # ===== РЕЖИМ: Список пользователей =====
    Format(
        "👥 <b>Управление пользователями</b>\n\n"
        "Всего пользователей: {users_count}\n\n"
        "Роли:\n"
        "👑 Владелец\n"
        "📊 Менеджер\n"
        "👷 Работник\n"
        "💳 Плательщик",
        when=lambda data, widget, manager: data["mode"] == "list",
    ),

    # Список пользователей (показываем только в режиме list)
    ScrollingGroup(
        Select(
            Format("{item[billing_emoji]}{item[role_emoji]} {item[display_name]}"),
            id="user_select",
            item_id_getter=lambda x: x["id"],
            items="users",
            on_click=on_user_selected,
        ),
        id="users_scroll",
        width=1,
        height=5,
        when=lambda data, widget, manager: data["mode"] == "list",
    ),

    # Кнопка создания (только для владельцев в режиме list)
    Button(
        Const("➕ Создать пользователя"),
        id="create_user",
        on_click=on_switch_to_create,
        when=lambda data, widget, manager: data["mode"] == "list" and data["is_owner"],
    ),

    # ===== РЕЖИМ: Создание пользователя =====
    Format(
        "➕ <b>Создание пользователя</b>",
        when=lambda data, widget, manager: data["mode"] == "create" and data["step"] == "",
    ),

    # Промпты для создания
    Format(
        "➕ <b>Создание пользователя</b>\n\n"
        "Шаг 1/4: Введите Telegram username:\n"
        "<i>Например: @example или example</i>",
        when=lambda data, widget, manager: data["mode"] == "create" and data["step"] == "username",
    ),

    Format(
        "\n{error}",
        when=lambda data, widget, manager: data["mode"] == "create" and data["step"] == "username" and data.get("error"),
    ),

    # Выбор пользователя Tracker
    Format(
        "➕ <b>Создание пользователя</b>\n\n"
        "Шаг 2/4: Выберите пользователя Yandex Tracker:\n"
        "Telegram: @{new_user_data[username]}\n\n"
        "Или пропустите, если пользователь не работает с Tracker",
        when=lambda data, widget, manager: data["mode"] == "create" and data["step"] == "select_tracker_user",
    ),

    ScrollingGroup(
        Select(
            Format("{item[display]} ({item[login]})"),
            id="tracker_user_select",
            item_id_getter=lambda x: x["login"],
            items="tracker_users",
            on_click=on_tracker_user_selected,
        ),
        id="tracker_users_scroll",
        width=1,
        height=6,
        when=lambda data, widget, manager: data["mode"] == "create" and data["step"] == "select_tracker_user",
    ),

    Button(
        Const("⏭️ Пропустить tracker"),
        id="skip_tracker",
        on_click=on_skip_tracker,
        when=lambda data, widget, manager: data["mode"] == "create" and data["step"] == "select_tracker_user",
    ),

    Button(
        Const("❌ Отмена"),
        id="cancel_create_tracker",
        on_click=on_switch_to_list,
        when=lambda data, widget, manager: data["mode"] == "create" and data["step"] == "select_tracker_user",
    ),

    # Ввод ФИО вручную (если пропустили Tracker)
    Format(
        "➕ <b>Создание пользователя</b>\n\n"
        "Шаг 2.5/4: Введите ФИО пользователя:\n"
        "Telegram: @{new_user_data[username]}\n\n"
        "<i>Например: Иван Иванов</i>",
        when=lambda data, widget, manager: data["mode"] == "create" and data["step"] == "enter_display_name",
    ),

    Format(
        "\n{error}",
        when=lambda data, widget, manager: data["mode"] == "create" and data["step"] == "enter_display_name" and data.get("error"),
    ),

    Format(
        "➕ <b>Создание пользователя</b>\n\n"
        "Шаг 3/4: Выберите роль:\n\n"
        "Telegram: @{new_user_data[username]}\n"
        "Tracker: {tracker_login_display}",
        when=lambda data, widget, manager: data["mode"] == "create" and data["step"] == "role",
    ),

    ScrollingGroup(
        Select(
            Format("{item[name]}"),
            id="role_select",
            item_id_getter=lambda x: x["id"],
            items="roles",
            on_click=on_role_selected,
        ),
        id="roles_scroll",
        width=1,
        height=3,
        when=lambda data, widget, manager: data["mode"] == "create" and data["step"] == "role",
    ),

    # Выбор плательщика
    Format(
        "➕ <b>Создание пользователя</b>\n\n"
        "Шаг 4/4: Будет ли пользователь плательщиком?\n\n"
        "Telegram: @{new_user_data[username]}\n"
        "Tracker: {tracker_login_display}\n"
        "Роль: {role_display_ru}",
        when=lambda data, widget, manager: data["mode"] == "create" and data["step"] == "billing_contact",
    ),

    ScrollingGroup(
        Select(
            Format("{item[name]}"),
            id="billing_contact_select",
            item_id_getter=lambda x: x["id"],
            items="billing_contact_options",
            on_click=on_billing_contact_selected,
        ),
        id="billing_contact_scroll",
        width=1,
        height=2,
        when=lambda data, widget, manager: data["mode"] == "create" and data["step"] == "billing_contact",
    ),

    Button(
        Const("❌ Отмена"),
        id="cancel_create",
        on_click=on_switch_to_list,
        when=lambda data, widget, manager: data["mode"] == "create" and data["step"] != "select_tracker_user",
    ),

    # ===== РЕЖИМ: Редактирование пользователя =====
    Format(
        "✏️ <b>Редактирование пользователя</b>\n\n"
        "ФИО: {selected_user[display_name]}\n"
        "Telegram ID: {selected_user[telegram_id]}\n"
        "Username: {selected_user[username]}\n"
        "Tracker: {selected_user[tracker]}\n"
        "Роль: {selected_user[role_display]}\n"
        "Плательщик: {selected_user[billing_status]}",
        when=lambda data, widget, manager: data["mode"] == "edit" and data["step"] == "",
    ),

    # Кнопки редактирования полей
    Button(
        Const("Username"),
        id="username",
        on_click=on_edit_field,
        when=lambda data, widget, manager: data["mode"] == "edit" and data["step"] == "" and data["is_owner"],
    ),
    Button(
        Const("Tracker"),
        id="tracker_login",
        on_click=on_edit_field,
        when=lambda data, widget, manager: data["mode"] == "edit" and data["step"] == "" and data["is_owner"],
    ),
    Button(
        Const("Роль"),
        id="role",
        on_click=on_edit_field,
        when=lambda data, widget, manager: data["mode"] == "edit" and data["step"] == "" and data["is_owner"],
    ),
    Button(
        Format("💳 Плательщик: {selected_user[billing_status]}"),
        id="toggle_billing",
        on_click=on_toggle_billing_contact,
        when=lambda data, widget, manager: data["mode"] == "edit" and data["step"] == "" and data["is_owner"],
    ),

    # Промпты для редактирования
    Const(
        "Введите новый username:",
        when=lambda data, widget, manager: data["mode"] == "edit" and data["step"] == "username",
    ),

    Format(
        "\n{error}",
        when=lambda data, widget, manager: data["mode"] == "edit" and data["step"] == "username" and data.get("error"),
    ),

    Button(
        Const("⬅️ Назад"),
        id="back_from_username_edit",
        on_click=on_back_from_edit_step,
        when=lambda data, widget, manager: data["mode"] == "edit" and data["step"] == "username",
    ),

    Const(
        "Выберите нового пользователя Tracker:",
        when=lambda data, widget, manager: data["mode"] == "edit" and data["step"] == "tracker_login",
    ),

    ScrollingGroup(
        Select(
            Format("{item[display]} ({item[login]})"),
            id="edit_tracker_user_select",
            item_id_getter=lambda x: x["login"],
            items="tracker_users",
            on_click=on_edit_tracker_user_selected,
        ),
        id="edit_tracker_users_scroll",
        width=1,
        height=8,
        when=lambda data, widget, manager: data["mode"] == "edit" and data["step"] == "tracker_login",
    ),

    Button(
        Const("⬅️ Назад"),
        id="back_from_tracker_edit",
        on_click=on_back_from_edit_step,
        when=lambda data, widget, manager: data["mode"] == "edit" and data["step"] == "tracker_login",
    ),

    Const(
        "Выберите новую роль:",
        when=lambda data, widget, manager: data["mode"] == "edit" and data["step"] == "role",
    ),

    ScrollingGroup(
        Select(
            Format("{item[name]}"),
            id="edit_role_select",
            item_id_getter=lambda x: x["id"],
            items="roles",
            on_click=on_edit_role_selected,
        ),
        id="edit_roles_scroll",
        width=1,
        height=3,
        when=lambda data, widget, manager: data["mode"] == "edit" and data["step"] == "role",
    ),

    Button(
        Const("⬅️ Назад"),
        id="back_from_role_edit",
        on_click=on_back_from_edit_step,
        when=lambda data, widget, manager: data["mode"] == "edit" and data["step"] == "role",
    ),

    Button(
        Const("🗑 Удалить пользователя"),
        id="delete_user",
        on_click=on_switch_to_delete,
        when=lambda data, widget, manager: data["mode"] == "edit" and data["step"] == "" and data["is_owner"],
    ),

    Button(
        Const("⬅️ Назад"),
        id="back_from_edit",
        on_click=on_switch_to_list,
        when=lambda data, widget, manager: data["mode"] == "edit" and data["step"] == "",
    ),

    # ===== РЕЖИМ: Удаление пользователя =====
    Format(
        "🗑 <b>Удаление пользователя</b>\n\n"
        "Вы уверены что хотите удалить пользователя?\n\n"
        "Username: {selected_user[username]}\n"
        "Tracker: {selected_user[tracker]}",
        when=lambda data, widget, manager: data["mode"] == "delete",
    ),

    Button(
        Const("✅ Да, удалить"),
        id="confirm_delete",
        on_click=on_delete_user_confirm,
        when=lambda data, widget, manager: data["mode"] == "delete",
    ),
    Button(
        Const("❌ Отмена"),
        id="cancel_delete",
        on_click=on_switch_to_list,
        when=lambda data, widget, manager: data["mode"] == "delete",
    ),

    # ===== ОБЩЕЕ =====
    Cancel(Const("🏠 Главное меню")),

    # MessageInput для single window
    MessageInput(on_text_input),

    state=UserManagement.main,
    getter=get_user_management_data,
)
