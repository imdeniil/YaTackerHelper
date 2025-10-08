"""Диалог управления пользователями (CRUD)

Single window интерфейс с режимами:
- list: Просмотр списка пользователей
- create: Создание нового пользователя
- edit: Редактирование пользователя
- delete: Удаление пользователя
"""
import logging
from typing import Any
from aiogram.types import CallbackQuery, Message
from aiogram_dialog import Dialog, Window, DialogManager, ShowMode
from aiogram_dialog.widgets.text import Const, Format
from aiogram_dialog.widgets.kbd import Button, ScrollingGroup, Select, Back, Cancel
from aiogram_dialog.widgets.input import MessageInput
from sqlalchemy.exc import IntegrityError

from bot.states import UserManagement
from bot.database import get_session, UserCRUD, UserRole
from src.tracker_client import TrackerClient

logger = logging.getLogger(__name__)


# ============ Data Getters ============

async def get_user_management_data(dialog_manager: DialogManager, **kwargs) -> dict[str, Any]:
    """Получает данные для окна управления пользователями"""
    mode = dialog_manager.dialog_data.get("mode", "list")
    step = dialog_manager.dialog_data.get("step", "")

    # Получаем список пользователей бота
    async with get_session() as session:
        users = await UserCRUD.get_all_users(session)

    # Текущий пользователь из middleware
    current_user = kwargs.get("event_from_user", {})
    user = kwargs.get("user")

    # Маппинг ролей для отображения
    role_mapping = {
        "owner": {"emoji": "👑", "display": "👑 Владелец"},
        "manager": {"emoji": "📊", "display": "📊 Менеджер"},
        "worker": {"emoji": "👷", "display": "👷 Работник"},
    }

    # Форматируем пользователей для отображения
    users_list = [
        {
            "id": str(u.id),
            "telegram_id": u.telegram_id,
            "username": u.telegram_username or "—",
            "tracker": u.tracker_login,
            "display_name": u.display_name,
            "role": u.role.value,
            "role_emoji": role_mapping.get(u.role.value, {}).get("emoji", "❓"),
            "role_display": role_mapping.get(u.role.value, {}).get("display", u.role.value),
        }
        for u in users
    ]

    # Данные для создания/редактирования
    selected_user_id = dialog_manager.dialog_data.get("selected_user_id")
    new_user_data = dialog_manager.dialog_data.get("new_user_data", {})

    # Находим выбранного пользователя
    selected_user = None
    if selected_user_id:
        for u in users:
            if u.id == int(selected_user_id):
                selected_user = {
                    "id": str(u.id),
                    "telegram_id": u.telegram_id,
                    "username": u.telegram_username or "—",
                    "tracker": u.tracker_login,
                    "display_name": u.display_name,
                    "role": u.role.value,
                    "role_display": role_mapping.get(u.role.value, {}).get("display", u.role.value),
                }
                break

    # Получаем список пользователей Tracker для выбора
    tracker_users = []
    tracker_users_map = {}  # Маппинг login -> display для сохранения display_name
    if step == "select_tracker_user" or (mode == "edit" and step == "tracker_login"):
        try:
            async with TrackerClient() as tracker:
                tracker_users_raw = await tracker.client.users.get()
                tracker_users = [
                    {
                        "login": u.get("login", ""),
                        "display": u.get("display", u.get("login", "")),
                    }
                    for u in tracker_users_raw
                    if not u.get("dismissed", False)  # Только активные
                ]
                # Создаем маппинг для быстрого доступа
                tracker_users_map = {
                    u["login"]: u["display"] for u in tracker_users
                }
                logger.info(f"Loaded {len(tracker_users)} active tracker users")
        except Exception as e:
            logger.error(f"Error fetching tracker users: {e}", exc_info=True)

    # Список ролей для выбора
    roles_list = [
        {"id": "owner", "name": "👑 Владелец"},
        {"id": "manager", "name": "📊 Менеджер"},
        {"id": "worker", "name": "👷 Работник"},
    ]

    # Сохраняем tracker_users_map в dialog_data для использования в обработчиках
    if tracker_users_map:
        dialog_manager.dialog_data["tracker_users_map"] = tracker_users_map

    return {
        "mode": mode,
        "step": step,
        "users": users_list,
        "users_count": len(users_list),
        "current_user_role": user.role.value if user else "worker",
        "is_owner": user.role == UserRole.OWNER if user else False,
        "selected_user": selected_user,
        "new_user_data": new_user_data,
        "tracker_users": tracker_users,
        "roles": roles_list,
        "error": dialog_manager.dialog_data.get("error"),
    }


# ============ Button Handlers ============

async def on_switch_to_create(callback: CallbackQuery, button: Button, manager: DialogManager):
    """Переключение в режим создания пользователя"""
    manager.dialog_data["mode"] = "create"
    manager.dialog_data["step"] = "username"
    manager.dialog_data["new_user_data"] = {}
    manager.dialog_data.pop("error", None)  # Очищаем предыдущие ошибки
    manager.show_mode = ShowMode.EDIT
    await manager.update({})


async def on_switch_to_list(callback: CallbackQuery, button: Button, manager: DialogManager):
    """Возврат к списку пользователей"""
    manager.dialog_data["mode"] = "list"
    manager.dialog_data["step"] = ""
    manager.dialog_data.pop("selected_user_id", None)
    manager.dialog_data.pop("new_user_data", None)
    manager.dialog_data.pop("error", None)  # Очищаем ошибки
    manager.show_mode = ShowMode.EDIT
    await manager.update({})


async def on_user_selected(callback: CallbackQuery, widget: Select, manager: DialogManager, item_id: str):
    """Обработка выбора пользователя для редактирования"""
    manager.dialog_data["mode"] = "edit"
    manager.dialog_data["selected_user_id"] = item_id
    manager.show_mode = ShowMode.EDIT
    await manager.update({})


async def on_delete_user_confirm(callback: CallbackQuery, button: Button, manager: DialogManager):
    """Подтверждение удаления пользователя"""
    user_id = manager.dialog_data.get("selected_user_id")
    if not user_id:
        await callback.answer("❌ Пользователь не выбран", show_alert=True)
        return

    async with get_session() as session:
        deleted = await UserCRUD.delete_user(session, int(user_id))

    if deleted:
        await callback.answer("✅ Пользователь удален", show_alert=True)
        await on_switch_to_list(callback, button, manager)
    else:
        await callback.answer("❌ Ошибка удаления", show_alert=True)


async def on_switch_to_delete(callback: CallbackQuery, button: Button, manager: DialogManager):
    """Переключение в режим удаления"""
    manager.dialog_data["mode"] = "delete"
    manager.show_mode = ShowMode.EDIT
    await manager.update({})


# ============ Input Handlers ============

async def on_text_input(message: Message, widget: MessageInput, manager: DialogManager):
    """Обработка текстового ввода в зависимости от шага"""
    mode = manager.dialog_data.get("mode")
    step = manager.dialog_data.get("step")

    if mode == "create":
        await handle_create_input(message.text, step, manager)
    elif mode == "edit":
        await handle_edit_input(message.text, step, manager)

    # Обновляем диалог
    manager.show_mode = ShowMode.EDIT
    await manager.update({})


async def handle_create_input(text: str, step: str, manager: DialogManager):
    """Обработка ввода при создании пользователя"""
    new_user_data = manager.dialog_data.get("new_user_data", {})

    if step == "username":
        # Убираем @ если есть
        username = text.lstrip("@")
        if username:
            new_user_data["username"] = username
            manager.dialog_data["step"] = "select_tracker_user"
            manager.dialog_data.pop("error", None)  # Очищаем ошибку при успехе
        else:
            manager.dialog_data["error"] = "❌ Username не может быть пустым"

    manager.dialog_data["new_user_data"] = new_user_data


async def handle_edit_input(text: str, step: str, manager: DialogManager):
    """Обработка ввода при редактировании пользователя"""
    user_id = manager.dialog_data.get("selected_user_id")
    if not user_id:
        return

    # Очищаем предыдущую ошибку
    manager.dialog_data.pop("error", None)

    try:
        async with get_session() as session:
            if step == "username":
                username = text.lstrip("@")
                if not username:
                    manager.dialog_data["error"] = "❌ Username не может быть пустым"
                    return
                await UserCRUD.update_user(session, int(user_id), telegram_username=username)

        # Возвращаемся к просмотру пользователя
        manager.dialog_data["step"] = ""
    except IntegrityError as e:
        error_str = str(e)
        # Обработка различных типов IntegrityError
        if "duplicate key" in error_str and "telegram_username" in error_str:
            manager.dialog_data["error"] = f"❌ Username '{text.lstrip('@')}' уже занят другим пользователем"
        elif "not-null constraint" in error_str and "telegram_username" in error_str:
            manager.dialog_data["error"] = "❌ Username обязателен для заполнения"
        else:
            manager.dialog_data["error"] = "❌ Ошибка обновления данных"
        logger.error(f"IntegrityError при обновлении пользователя: {e}")
        # Остаемся на текущем шаге, чтобы пользователь мог исправить
    except Exception as e:
        manager.dialog_data["error"] = "❌ Произошла ошибка при обновлении"
        logger.error(f"Unexpected error при обновлении пользователя: {e}", exc_info=True)


async def create_user_from_data(data: dict, manager: DialogManager) -> bool:
    """Создает пользователя из собранных данных

    Returns:
        bool: True если пользователь успешно создан, False при ошибке
    """
    try:
        role = UserRole[data["role"].upper()]
        async with get_session() as session:
            await UserCRUD.create_user(
                session=session,
                telegram_username=data["username"],
                tracker_login=data["tracker_login"],
                display_name=data["display_name"],
                role=role,
            )
        return True
    except IntegrityError as e:
        error_str = str(e)
        # Обработка различных типов IntegrityError
        if "duplicate key" in error_str and "telegram_username" in error_str:
            manager.dialog_data["error"] = f"❌ Username '{data['username']}' уже существует"
        elif "not-null constraint" in error_str and "telegram_username" in error_str:
            manager.dialog_data["error"] = "❌ Username обязателен для заполнения"
        else:
            manager.dialog_data["error"] = "❌ Ошибка создания пользователя"
        logger.error(f"IntegrityError при создании пользователя: {e}")
        # Возвращаемся к шагу ввода username
        manager.dialog_data["step"] = "username"
        return False
    except Exception as e:
        manager.dialog_data["error"] = "❌ Произошла ошибка при создании пользователя"
        logger.error(f"Unexpected error при создании пользователя: {e}", exc_info=True)
        manager.dialog_data["step"] = "username"
        return False


async def on_tracker_user_selected(callback: CallbackQuery, widget: Select, manager: DialogManager, item_id: str):
    """Обработка выбора пользователя Tracker"""
    new_user_data = manager.dialog_data.get("new_user_data", {})
    new_user_data["tracker_login"] = item_id

    # Сохраняем display_name из маппинга
    tracker_users_map = manager.dialog_data.get("tracker_users_map", {})
    display_name = tracker_users_map.get(item_id, item_id)  # Fallback на login если нет display
    new_user_data["display_name"] = display_name

    manager.dialog_data["new_user_data"] = new_user_data
    manager.dialog_data["step"] = "role"
    manager.dialog_data.pop("error", None)  # Очищаем ошибки
    manager.show_mode = ShowMode.EDIT
    await manager.update({})


async def on_role_selected(callback: CallbackQuery, widget: Select, manager: DialogManager, item_id: str):
    """Обработка выбора роли"""
    new_user_data = manager.dialog_data.get("new_user_data", {})
    new_user_data["role"] = item_id
    manager.dialog_data["new_user_data"] = new_user_data

    # Создаем пользователя
    success = await create_user_from_data(new_user_data, manager)

    if success:
        # Возвращаемся к списку только при успехе
        manager.dialog_data["mode"] = "list"
        manager.dialog_data["step"] = ""
        manager.dialog_data.pop("new_user_data", None)
    # Если ошибка - остаемся в режиме создания на шаге username (устанавливается в create_user_from_data)

    manager.show_mode = ShowMode.EDIT
    await manager.update({})


async def on_edit_field(callback: CallbackQuery, button: Button, manager: DialogManager):
    """Переключение в режим редактирования поля"""
    field = button.widget_id  # username, tracker_login, role
    manager.dialog_data["step"] = field
    manager.dialog_data.pop("error", None)  # Очищаем предыдущие ошибки
    manager.show_mode = ShowMode.EDIT
    await manager.update({})


async def on_edit_role_selected(callback: CallbackQuery, widget: Select, manager: DialogManager, item_id: str):
    """Обработка выбора роли при редактировании"""
    user_id = manager.dialog_data.get("selected_user_id")
    if not user_id:
        return

    async with get_session() as session:
        role = UserRole[item_id.upper()]
        await UserCRUD.update_user(session, int(user_id), role=role)

    # Возвращаемся к просмотру пользователя
    manager.dialog_data["step"] = ""
    manager.show_mode = ShowMode.EDIT
    await manager.update({})


async def on_edit_tracker_user_selected(callback: CallbackQuery, widget: Select, manager: DialogManager, item_id: str):
    """Обработка выбора трекер-пользователя при редактировании"""
    user_id = manager.dialog_data.get("selected_user_id")
    if not user_id:
        return

    # Получаем display_name из маппинга
    tracker_users_map = manager.dialog_data.get("tracker_users_map", {})
    display_name = tracker_users_map.get(item_id, item_id)

    async with get_session() as session:
        await UserCRUD.update_user(
            session,
            int(user_id),
            tracker_login=item_id,
            display_name=display_name
        )

    # Возвращаемся к просмотру пользователя
    manager.dialog_data["step"] = ""
    manager.show_mode = ShowMode.EDIT
    await manager.update({})


async def on_back_from_edit_step(callback: CallbackQuery, button: Button, manager: DialogManager):
    """Возврат из режима редактирования поля к просмотру пользователя"""
    manager.dialog_data["step"] = ""
    manager.show_mode = ShowMode.EDIT
    await manager.update({})


# ============ Dialog Windows ============

user_management_window = Window(
    # ===== РЕЖИМ: Список пользователей =====
    Format(
        "👥 <b>Управление пользователями</b>\n\n"
        "Всего пользователей: {users_count}\n\n"
        "Роли:\n"
        "👑 Владелец\n"
        "📊 Менеджер\n"
        "👷 Работник",
        when=lambda data, widget, manager: data["mode"] == "list",
    ),

    # Список пользователей (показываем только в режиме list)
    ScrollingGroup(
        Select(
            Format("{item[role_emoji]} {item[display_name]}"),
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
        "Шаг 1/3: Введите Telegram username:\n"
        "<i>Например: @Nata3D1040 или Nata3D1040</i>",
        when=lambda data, widget, manager: data["mode"] == "create" and data["step"] == "username",
    ),

    Format(
        "\n{error}",
        when=lambda data, widget, manager: data["mode"] == "create" and data["step"] == "username" and data.get("error"),
    ),

    # Выбор пользователя Tracker
    Format(
        "➕ <b>Создание пользователя</b>\n\n"
        "Шаг 2/3: Выберите пользователя Yandex Tracker:\n"
        "Telegram: @{new_user_data[username]}",
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
        height=8,
        when=lambda data, widget, manager: data["mode"] == "create" and data["step"] == "select_tracker_user",
    ),

    Format(
        "➕ <b>Создание пользователя</b>\n\n"
        "Шаг 3/3: Выберите роль:\n\n"
        "Telegram: @{new_user_data[username]}\n"
        "Tracker: {new_user_data[tracker_login]}",
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

    Button(
        Const("❌ Отмена"),
        id="cancel_create",
        on_click=on_switch_to_list,
        when=lambda data, widget, manager: data["mode"] == "create",
    ),

    # ===== РЕЖИМ: Редактирование пользователя =====
    Format(
        "✏️ <b>Редактирование пользователя</b>\n\n"
        "ФИО: {selected_user[display_name]}\n"
        "Telegram ID: {selected_user[telegram_id]}\n"
        "Username: {selected_user[username]}\n"
        "Tracker: {selected_user[tracker]}\n"
        "Роль: {selected_user[role_display]}",
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


# Создаем диалог
user_management_dialog = Dialog(user_management_window)
