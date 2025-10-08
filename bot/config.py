"""Конфигурация бота."""

import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class BotConfig:
    """Конфигурация Telegram бота."""

    bot_token: str
    tracker_api_key: str
    tracker_org_id: str

    @classmethod
    def from_env(cls) -> "BotConfig":
        """
        Загрузить конфигурацию из переменных окружения.

        Returns:
            BotConfig с загруженными данными

        Raises:
            ValueError: Если отсутствуют обязательные переменные
        """
        bot_token = os.getenv("BOT_TOKEN")
        if not bot_token:
            raise ValueError("BOT_TOKEN не найден в .env файле")

        tracker_api_key = os.getenv("TRACKER_API_KEY")
        if not tracker_api_key:
            raise ValueError("TRACKER_API_KEY не найден в .env файле")

        tracker_org_id = os.getenv("TRACKER_ORG_ID")
        if not tracker_org_id:
            raise ValueError("TRACKER_ORG_ID не найден в .env файле")

        return cls(
            bot_token=bot_token,
            tracker_api_key=tracker_api_key,
            tracker_org_id=tracker_org_id,
        )
