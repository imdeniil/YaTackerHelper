"""Конфигурация веб-приложения"""

import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class WebConfig:
    """Конфигурация веб-приложения"""

    # Telegram Bot для отправки уведомлений и файлов
    bot_token: str

    # Секретный ключ для сессий
    secret_key: str

    # URL базы данных (общая с ботом)
    database_url: str

    # Порт для веб-приложения
    port: int = 8000

    # Host для веб-приложения
    host: str = "0.0.0.0"

    # ID приватной группы для хранения файлов
    storage_chat_id: int = 0

    @classmethod
    def from_env(cls) -> "WebConfig":
        """Загрузить конфигурацию из переменных окружения

        Returns:
            WebConfig с загруженными данными

        Raises:
            ValueError: Если отсутствуют обязательные переменные
        """
        bot_token = os.getenv("BOT_TOKEN")
        if not bot_token:
            raise ValueError("BOT_TOKEN не найден в .env файле")

        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            raise ValueError("DATABASE_URL не найден в .env файле")

        # Генерируем secret_key или берем из .env
        secret_key = os.getenv("WEB_SECRET_KEY")
        if not secret_key:
            # Если не указан - генерируем случайный (для dev)
            import secrets
            secret_key = secrets.token_hex(32)
            print(f"⚠️  WEB_SECRET_KEY не установлен в .env, используется случайный: {secret_key[:16]}...")

        storage_chat_id = os.getenv("STORAGE_CHAT_ID")
        if not storage_chat_id:
            raise ValueError(
                "STORAGE_CHAT_ID не найден в .env файле\n"
                "Создайте приватную группу для хранения файлов и добавьте бота в неё.\n"
                "Затем укажите chat_id группы в STORAGE_CHAT_ID"
            )

        port = int(os.getenv("WEB_PORT", "8000"))
        host = os.getenv("WEB_HOST", "0.0.0.0")

        return cls(
            bot_token=bot_token,
            secret_key=secret_key,
            database_url=database_url,
            port=port,
            host=host,
            storage_chat_id=int(storage_chat_id),
        )
