"""Data getters для диалога настроек пользователя"""

import logging
from typing import Any
from aiogram_dialog import DialogManager

from bot.database import UserRole
from src.tracker_client import TrackerClient

logger = logging.getLogger(__name__)


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
