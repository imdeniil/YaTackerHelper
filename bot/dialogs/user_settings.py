"""Диалог настроек пользователя

Single window интерфейс для изменения настроек пользователя:
- Очередь по умолчанию
- Портфель по умолчанию
"""
import logging
from typing import Any
from aiogram.types import CallbackQuery, Message
from aiogram_dialog import Dialog, Window, DialogManager
from aiogram_dialog.widgets.text import Const, Format
from aiogram_dialog.widgets.kbd import Button, Cancel, ScrollingGroup, Select
from aiogram_dialog.widgets.input import MessageInput

from bot.states import UserSettings as UserSettingsState
from bot.database import get_session, UserCRUD, UserRole
from src.tracker_client import TrackerClient

logger = logging.getLogger(__name__)

# ============ Data Getters ============

async def get_user_settings_data(dialog_manager: DialogManager, **kwargs) -> dict[str, Any]:
    """Получает данные для окна настроек пользователя"""
    user = kwargs.get("user")
    user_settings = kwargs.get("user_settings")

    step = dialog_manager.dialog_data.get("step", "")

    # Если редактируем очередь или портфель - получаем список из API
    queues = []
    portfolios = []

    # Получаем название текущего портфеля для отображения
    portfolio_name = None
    if user_settings and user_settings.default_portfolio and step == "":
        try:
            async with TrackerClient() as tracker:
                portfolio_data = await tracker.client.entities.get(
                    entity_id=user_settings.default_portfolio,
                    entity_type="portfolio",
                    fields="summary"
                )
                if portfolio_data:
                    fields_dict = portfolio_data.get("fields", {})
                    portfolio_name = fields_dict.get("summary") or f"Портфель #{portfolio_data.get('shortId')}"
        except Exception as e:
            logger.error(f"Error fetching portfolio name: {e}")
            portfolio_name = user_settings.default_portfolio

    if step == "select_queue":
        # Получаем список очередей
        try:
            async with TrackerClient() as tracker:
                queues_raw = await tracker.client.queues.get()
                logger.info(f"Fetched {len(queues_raw) if queues_raw else 0} queues from API")
                logger.info(f"Sample queue: {queues_raw[0] if queues_raw else 'None'}")
                queues = [
                    {"key": q.get("key", ""), "name": q.get("name", q.get("key", ""))}
                    for q in queues_raw
                ]
                logger.info(f"Processed {len(queues)} queues")
        except Exception as e:
            logger.error(f"Error fetching queues: {e}", exc_info=True)

    elif step == "select_portfolio":
        # Получаем список портфелей
        try:
            async with TrackerClient() as tracker:
                # Запрашиваем портфели с полем summary
                portfolios_raw = await tracker.client.entities.search(
                    entity_type="portfolio",
                    fields="summary"
                )

                logger.info(f"Raw portfolios response type: {type(portfolios_raw)}")

                # Обработка пагинации
                if isinstance(portfolios_raw, dict):
                    pages = portfolios_raw.get("pages", 1)
                    if isinstance(pages, int) and pages > 1:
                        per_page = pages * 50
                        portfolios_raw = await tracker.client.entities.search(
                            entity_type="portfolio",
                            fields="summary",
                            per_page=per_page,
                        )
                    if "values" in portfolios_raw:
                        portfolios_raw = portfolios_raw["values"]

                logger.info(f"Fetched {len(portfolios_raw) if portfolios_raw else 0} portfolios from API")

                # Формируем список портфелей с человекочитаемыми именами
                portfolios = []
                for p in portfolios_raw:
                    fields_dict = p.get("fields", {})
                    # Название из fields.summary или fallback на shortId
                    name = (
                        fields_dict.get("summary") or
                        f"Портфель #{p.get('shortId', p.get('id', ''))}"
                    )
                    portfolios.append({
                        "id": p.get("id", ""),
                        "name": name
                    })

                logger.info(f"Processed {len(portfolios)} portfolios with names from fields.summary")
        except Exception as e:
            logger.error(f"Error fetching portfolios: {e}", exc_info=True)

    return {
        "step": step,
        "username": user.telegram_username or "пользователь" if user else "гость",
        "default_queue": user_settings.default_queue if user_settings else "ZADACIBMT",
        "default_portfolio": user_settings.default_portfolio if user_settings else "65cde69d486b9524503455b7",
        "default_portfolio_name": portfolio_name or (user_settings.default_portfolio if user_settings else "65cde69d486b9524503455b7"),
        "queues": queues,
        "portfolios": portfolios,
        "is_manager_or_owner": user.role in [UserRole.OWNER, UserRole.MANAGER] if user else False,
    }


# ============ Button Handlers ============

async def on_edit_queue(callback: CallbackQuery, button: Button, manager: DialogManager):
    """Переключение в режим редактирования очереди"""
    manager.dialog_data["step"] = "select_queue"
    await manager.update({})


async def on_edit_portfolio(callback: CallbackQuery, button: Button, manager: DialogManager):
    """Переключение в режим редактирования портфеля"""
    manager.dialog_data["step"] = "select_portfolio"
    await manager.update({})


async def on_queue_selected(callback: CallbackQuery, widget: Select, manager: DialogManager, item_id: str):
    """Обработка выбора очереди"""
    user = manager.middleware_data.get("user")
    if not user:
        return

    async with get_session() as session:
        # Обновляем настройки в БД
        updated_settings = await UserCRUD.update_user_settings(session, user.id, default_queue=item_id)

        # Обновляем настройки в middleware_data для отображения
        if updated_settings:
            manager.middleware_data["user_settings"] = updated_settings

    # Возвращаемся к главному экрану без alert
    manager.dialog_data["step"] = ""
    await manager.update({})


async def on_portfolio_selected(callback: CallbackQuery, widget: Select, manager: DialogManager, item_id: str):
    """Обработка выбора портфеля"""
    user = manager.middleware_data.get("user")
    if not user:
        return

    async with get_session() as session:
        # Обновляем настройки в БД
        updated_settings = await UserCRUD.update_user_settings(session, user.id, default_portfolio=item_id)

        # Обновляем настройки в middleware_data для отображения
        if updated_settings:
            manager.middleware_data["user_settings"] = updated_settings

    # Возвращаемся к главному экрану без alert
    manager.dialog_data["step"] = ""
    await manager.update({})


async def on_back_to_main(callback: CallbackQuery, button: Button, manager: DialogManager):
    """Возврат к главному экрану настроек"""
    manager.dialog_data["step"] = ""
    await manager.update({})


# ============ Dialog Window ============

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


# Создаем диалог
user_settings_dialog = Dialog(user_settings_window)
