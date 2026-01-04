"""Подключение к базе данных для веб-приложения

Переиспользует модели и CRUD из бота, но создает свой engine и session maker.
"""

import logging
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

# Импортируем модели из бота
from bot.database.models import Base, User, PaymentRequest, BillingNotification
from bot.database.crud import UserCRUD, PaymentRequestCRUD, BillingNotificationCRUD
from web.config import WebConfig

logger = logging.getLogger(__name__)

# Инициализируем после загрузки конфигурации
engine = None
async_session_maker = None


def init_database(config: WebConfig):
    """Инициализирует подключение к базе данных

    Args:
        config: Конфигурация веб-приложения
    """
    global engine, async_session_maker

    # Создаем движок
    engine = create_async_engine(
        config.database_url,
        echo=False,  # Включить для отладки SQL запросов
        future=True,
        pool_pre_ping=True,  # Проверка подключения перед использованием
    )

    # Создаем фабрику сессий
    async_session_maker = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    logger.info("✅ Подключение к БД инициализировано для веб-приложения")


@asynccontextmanager
async def get_session():
    """Async context manager для получения сессии БД

    Usage:
        async with get_session() as session:
            user = await UserCRUD.get_user_by_id(session, 1)
    """
    if async_session_maker is None:
        raise RuntimeError("База данных не инициализирована! Вызовите init_database() сначала.")

    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# Экспортируем для удобства
__all__ = [
    "init_database",
    "get_session",
    "User",
    "PaymentRequest",
    "BillingNotification",
    "UserCRUD",
    "PaymentRequestCRUD",
    "BillingNotificationCRUD",
]
