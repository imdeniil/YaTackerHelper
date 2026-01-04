"""Button handlers для диалога управления пользователями"""

import logging
from aiogram.types import CallbackQuery, Message
from aiogram_dialog import DialogManager, ShowMode
from aiogram_dialog.widgets.kbd import Button, Select
from aiogram_dialog.widgets.input import MessageInput
from sqlalchemy.exc import IntegrityError

from bot.database import get_session, UserCRUD, UserRole

logger = logging.getLogger(__name__)


# ============ Навигация между режимами ============

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


async def on_switch_to_delete(callback: CallbackQuery, button: Button, manager: DialogManager):
    """Переключение в режим удаления"""
    manager.dialog_data["mode"] = "delete"
    manager.show_mode = ShowMode.EDIT
    await manager.update({})


# ============ Удаление пользователя ============

async def on_delete_user_confirm(callback: CallbackQuery, button: Button, manager: DialogManager):
    """Подтверждение удаления пользователя"""
    user_id = manager.dialog_data.get("selected_user_id")
    if not user_id:
        await callback.answer("❌ Пользователь не выбран", show_alert=True)
        return

    async with get_session() as session:
        deleted = await UserCRUD.delete_user(session, int(user_id))

    if deleted:
        await callback.answer("✅ Пользователь удален")
        await on_switch_to_list(callback, button, manager)
    else:
        await callback.answer("❌ Ошибка удаления")


# ============ Создание пользователя ============

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


async def on_skip_tracker(callback: CallbackQuery, button: Button, manager: DialogManager):
    """Обработчик пропуска выбора пользователя Tracker"""
    # Пропускаем tracker_login, переходим к ручному вводу ФИО
    manager.dialog_data["step"] = "enter_display_name"
    manager.dialog_data.pop("error", None)
    manager.show_mode = ShowMode.EDIT
    await manager.update({})


async def on_role_selected(callback: CallbackQuery, widget: Select, manager: DialogManager, item_id: str):
    """Обработка выбора роли"""
    new_user_data = manager.dialog_data.get("new_user_data", {})
    new_user_data["role"] = item_id
    manager.dialog_data["new_user_data"] = new_user_data

    # Переходим к выбору billing контакта
    manager.dialog_data["step"] = "billing_contact"
    manager.dialog_data.pop("error", None)
    manager.show_mode = ShowMode.EDIT
    await manager.update({})


async def on_billing_contact_selected(callback: CallbackQuery, widget: Select, manager: DialogManager, item_id: str):
    """Обработка выбора статуса плательщика"""
    new_user_data = manager.dialog_data.get("new_user_data", {})
    new_user_data["is_billing_contact"] = item_id == "yes"
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
                display_name=data["display_name"],
                role=role,
                tracker_login=data.get("tracker_login"),  # Опциональный
                is_billing_contact=data.get("is_billing_contact", False),
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


# ============ Редактирование пользователя ============

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


async def on_toggle_billing_contact(callback: CallbackQuery, button: Button, manager: DialogManager):
    """Переключение статуса плательщика"""
    user_id = manager.dialog_data.get("selected_user_id")
    if not user_id:
        await callback.answer("❌ Пользователь не выбран", show_alert=True)
        return

    async with get_session() as session:
        user = await UserCRUD.toggle_billing_contact(session, int(user_id))

    if user:
        status = "включен" if user.is_billing_contact else "выключен"
        await callback.answer(f"✅ Плательщик {status}")
    else:
        await callback.answer("❌ Ошибка обновления")

    manager.show_mode = ShowMode.EDIT
    await manager.update({})


# ============ Обработка текстового ввода ============

async def on_text_input(message: Message, widget: MessageInput, manager: DialogManager):
    """Обработка текстового ввода в зависимости от шага"""
    if not message.text:
        await message.answer("❌ Пожалуйста, отправьте текстовое сообщение")
        return

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

    elif step == "enter_display_name":
        # Ввод ФИО вручную (если пропустили выбор Tracker)
        display_name = text.strip()
        if display_name:
            new_user_data["display_name"] = display_name
            new_user_data["tracker_login"] = None  # Явно устанавливаем None
            manager.dialog_data["step"] = "role"
            manager.dialog_data.pop("error", None)
        else:
            manager.dialog_data["error"] = "❌ ФИО не может быть пустым"

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
