import os
import logging
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from .models import Base

logger = logging.getLogger(__name__)

# PostgreSQL connection URL
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError(
        "DATABASE_URL не задан в переменных окружения!\n"
        "Пожалуйста, добавьте DATABASE_URL в .env файл.\n"
        "Пример: DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/yatrackerhelper"
    )

# Создаем движок
engine = create_async_engine(
    DATABASE_URL,
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


async def init_db():
    """Инициализирует базу данных, создавая все таблицы"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("✅ Таблицы базы данных созданы")


async def init_default_owners():
    """Создает дефолтных владельцев из .env при первом запуске"""
    from .crud import UserCRUD
    from .models import UserRole

    # Проверяем переменные окружения для владельцев
    owner1_username = os.getenv("OWNER1_USERNAME")
    owner1_tracker_login = os.getenv("OWNER1_TRACKER_LOGIN")
    owner1_display_name = os.getenv("OWNER1_DISPLAY_NAME")

    owner2_username = os.getenv("OWNER2_USERNAME")
    owner2_tracker_login = os.getenv("OWNER2_TRACKER_LOGIN")
    owner2_display_name = os.getenv("OWNER2_DISPLAY_NAME")

    # Если не указаны данные владельцев - пропускаем
    if not all([owner1_username, owner1_tracker_login, owner1_display_name]):
        logger.warning(
            "⚠️  Данные OWNER1 не указаны в .env - владелец не будет создан автоматически"
        )
        return

    async with get_session() as session:
        # Создаем Owner 1
        owner1 = await UserCRUD.get_user_by_username(session, owner1_username)
        if not owner1:
            await UserCRUD.create_user(
                session=session,
                telegram_username=owner1_username,
                tracker_login=owner1_tracker_login,
                display_name=owner1_display_name,
                role=UserRole.OWNER,
            )
            logger.info(
                f"✅ Создан владелец 1: @{owner1_username} ({owner1_display_name})"
            )
        else:
            logger.info(f"ℹ️  Владелец 1: @{owner1_username} уже существует")

        # Создаем Owner 2 (если указан)
        if all([owner2_username, owner2_tracker_login, owner2_display_name]):
            owner2 = await UserCRUD.get_user_by_username(session, owner2_username)
            if not owner2:
                await UserCRUD.create_user(
                    session=session,
                    telegram_username=owner2_username,
                    tracker_login=owner2_tracker_login,
                    display_name=owner2_display_name,
                    role=UserRole.OWNER,
                )
                logger.info(
                    f"✅ Создан владелец 2: @{owner2_username} ({owner2_display_name})"
                )
            else:
                logger.info(f"ℹ️  Владелец 2: @{owner2_username} уже существует")
        else:
            logger.info("ℹ️  Данные OWNER2 не указаны - второй владелец не создан")


@asynccontextmanager
async def get_session():
    """Async context manager для получения сессии БД

    Usage:
        async with get_session() as session:
            user = await session.get(User, 1)
    """
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
