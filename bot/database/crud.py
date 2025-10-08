from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from .models import User, UserSettings, UserRole


class UserCRUD:
    """CRUD операции для работы с пользователями"""

    @staticmethod
    async def create_user(
        session: AsyncSession,
        telegram_username: str,
        tracker_login: str,
        display_name: str,
        role: UserRole = UserRole.WORKER,
        telegram_id: Optional[int] = None,
        default_queue: str = "ZADACIBMT",
        default_portfolio: str = "65cde69d486b9524503455b7",
    ) -> User:
        """Создает нового пользователя с настройками по умолчанию

        Args:
            session: Сессия БД
            telegram_username: Username в Telegram (обязательный)
            tracker_login: Логин в Yandex Tracker
            display_name: ФИО пользователя (из Tracker)
            role: Роль пользователя
            telegram_id: ID пользователя в Telegram (опциональный, заполнится при первом входе)
            default_queue: Очередь по умолчанию
            default_portfolio: Портфель по умолчанию

        Returns:
            Созданный пользователь
        """
        user = User(
            telegram_id=telegram_id,
            telegram_username=telegram_username.lstrip("@"),  # Убираем @ если есть
            tracker_login=tracker_login,
            display_name=display_name,
            role=role,
        )
        session.add(user)
        await session.flush()

        # Создаем настройки для пользователя
        settings = UserSettings(
            user_id=user.id,
            default_queue=default_queue,
            default_portfolio=default_portfolio,
        )
        session.add(settings)
        await session.commit()
        await session.refresh(user)

        return user

    @staticmethod
    async def get_user_by_telegram_id(
        session: AsyncSession,
        telegram_id: int,
    ) -> Optional[User]:
        """Получает пользователя по Telegram ID с загруженными настройками

        Args:
            session: Сессия БД
            telegram_id: ID пользователя в Telegram

        Returns:
            Пользователь или None
        """
        query = (
            select(User)
            .options(selectinload(User.settings))
            .where(User.telegram_id == telegram_id)
        )
        result = await session.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_user_by_username(
        session: AsyncSession,
        username: str,
    ) -> Optional[User]:
        """Получает пользователя по username с загруженными настройками

        Args:
            session: Сессия БД
            username: Username в Telegram (без @)

        Returns:
            Пользователь или None
        """
        clean_username = username.lstrip("@")
        query = (
            select(User)
            .options(selectinload(User.settings))
            .where(User.telegram_username == clean_username)
        )
        result = await session.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_user_by_id(
        session: AsyncSession,
        user_id: int,
    ) -> Optional[User]:
        """Получает пользователя по внутреннему ID с загруженными настройками

        Args:
            session: Сессия БД
            user_id: Внутренний ID пользователя

        Returns:
            Пользователь или None
        """
        query = (
            select(User)
            .options(selectinload(User.settings))
            .where(User.id == user_id)
        )
        result = await session.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_all_users(session: AsyncSession) -> List[User]:
        """Получает всех пользователей с загруженными настройками

        Args:
            session: Сессия БД

        Returns:
            Список всех пользователей
        """
        query = select(User).options(selectinload(User.settings))
        result = await session.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def update_user(
        session: AsyncSession,
        user_id: int,
        **kwargs,
    ) -> Optional[User]:
        """Обновляет данные пользователя

        Args:
            session: Сессия БД
            user_id: ID пользователя
            **kwargs: Поля для обновления (telegram_username, tracker_login, display_name, role)

        Returns:
            Обновленный пользователь или None
        """
        user = await UserCRUD.get_user_by_id(session, user_id)
        if not user:
            return None

        for key, value in kwargs.items():
            if hasattr(user, key):
                setattr(user, key, value)

        await session.commit()
        await session.refresh(user)
        return user

    @staticmethod
    async def update_user_settings(
        session: AsyncSession,
        user_id: int,
        default_queue: Optional[str] = None,
        default_portfolio: Optional[str] = None,
    ) -> Optional[UserSettings]:
        """Обновляет настройки пользователя

        Args:
            session: Сессия БД
            user_id: ID пользователя
            default_queue: Новая очередь по умолчанию
            default_portfolio: Новый портфель по умолчанию

        Returns:
            Обновленные настройки или None
        """
        user = await UserCRUD.get_user_by_id(session, user_id)
        if not user or not user.settings:
            return None

        if default_queue is not None:
            user.settings.default_queue = default_queue
        if default_portfolio is not None:
            user.settings.default_portfolio = default_portfolio

        await session.commit()
        await session.refresh(user.settings)
        return user.settings

    @staticmethod
    async def delete_user(session: AsyncSession, user_id: int) -> bool:
        """Удаляет пользователя (и его настройки через cascade)

        Args:
            session: Сессия БД
            user_id: ID пользователя

        Returns:
            True если пользователь был удален, False если не найден
        """
        user = await UserCRUD.get_user_by_id(session, user_id)
        if not user:
            return False

        await session.delete(user)
        await session.commit()
        return True
