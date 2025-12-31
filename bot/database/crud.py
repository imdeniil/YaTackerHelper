from typing import Optional, List
from datetime import datetime, date
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from .models import User, UserSettings, UserRole, PaymentRequest, PaymentRequestStatus, BillingNotification

class UserCRUD:
    """CRUD операции для работы с пользователями"""

    @staticmethod
    async def create_user(
        session: AsyncSession,
        telegram_username: str,
        display_name: str,
        role: UserRole = UserRole.WORKER,
        tracker_login: Optional[str] = None,
        telegram_id: Optional[int] = None,
        is_billing_contact: bool = False,
        default_queue: str = "ZADACIBMT",
        default_portfolio: str = "65cde69d486b9524503455b7",
    ) -> User:
        """Создает нового пользователя с настройками по умолчанию

        Args:
            session: Сессия БД
            telegram_username: Username в Telegram (обязательный)
            display_name: ФИО пользователя (обязательный)
            role: Роль пользователя
            tracker_login: Логин в Yandex Tracker (опциональный, только для работы с Tracker)
            telegram_id: ID пользователя в Telegram (опциональный, заполнится при первом входе)
            is_billing_contact: Флаг контактного лица для счетов (по умолчанию False)
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
            is_billing_contact=is_billing_contact,
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

    @staticmethod
    async def toggle_billing_contact(
        session: AsyncSession,
        user_id: int,
    ) -> Optional[User]:
        """Переключает статус billing контакта для пользователя

        Args:
            session: Сессия БД
            user_id: ID пользователя

        Returns:
            Обновленный пользователь или None
        """
        user = await UserCRUD.get_user_by_id(session, user_id)
        if not user:
            return None

        user.is_billing_contact = not user.is_billing_contact
        await session.commit()
        await session.refresh(user)
        return user

    @staticmethod
    async def get_billing_contacts(session: AsyncSession) -> List[User]:
        """Получает всех пользователей отмеченных как billing контакты

        Args:
            session: Сессия БД

        Returns:
            Список пользователей с is_billing_contact=True
        """
        query = (
            select(User)
            .options(selectinload(User.settings))
            .where(User.is_billing_contact == True)
        )
        result = await session.execute(query)
        return list(result.scalars().all())


class PaymentRequestCRUD:
    """CRUD операции для работы с запросами на оплату"""

    @staticmethod
    async def create_payment_request(
        session: AsyncSession,
        created_by_id: int,
        title: str,
        amount: str,
        comment: str,
        invoice_file_id: Optional[str] = None,
    ) -> PaymentRequest:
        """Создает новый запрос на оплату

        Args:
            session: Сессия БД
            created_by_id: ID пользователя-создателя
            title: Название для плательщика
            amount: Сумма в рублях
            comment: Комментарий
            invoice_file_id: Telegram file_id счета (опционально)

        Returns:
            Созданный запрос на оплату
        """
        payment_request = PaymentRequest(
            created_by_id=created_by_id,
            title=title,
            amount=amount,
            comment=comment,
            invoice_file_id=invoice_file_id,
            status=PaymentRequestStatus.PENDING.value,
        )
        session.add(payment_request)
        await session.commit()
        await session.refresh(payment_request)
        return payment_request

    @staticmethod
    async def get_payment_request_by_id(
        session: AsyncSession,
        request_id: int,
    ) -> Optional[PaymentRequest]:
        """Получает запрос на оплату по ID с загруженными связями

        Args:
            session: Сессия БД
            request_id: ID запроса

        Returns:
            Запрос на оплату или None
        """
        query = (
            select(PaymentRequest)
            .options(
                selectinload(PaymentRequest.created_by),
                selectinload(PaymentRequest.processing_by),
                selectinload(PaymentRequest.paid_by),
            )
            .where(PaymentRequest.id == request_id)
        )
        result = await session.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_user_payment_requests(
        session: AsyncSession,
        user_id: int,
    ) -> List[PaymentRequest]:
        """Получает все запросы на оплату созданные пользователем

        Args:
            session: Сессия БД
            user_id: ID пользователя

        Returns:
            Список запросов пользователя
        """
        query = (
            select(PaymentRequest)
            .options(
                selectinload(PaymentRequest.created_by),
                selectinload(PaymentRequest.processing_by),
                selectinload(PaymentRequest.paid_by),
            )
            .where(PaymentRequest.created_by_id == user_id)
            .order_by(PaymentRequest.created_at.desc())
        )
        result = await session.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def get_all_payment_requests(
        session: AsyncSession,
        status: Optional[PaymentRequestStatus] = None,
    ) -> List[PaymentRequest]:
        """Получает все запросы на оплату (для billing контактов)

        Args:
            session: Сессия БД
            status: Фильтр по статусу (опционально)

        Returns:
            Список всех запросов
        """
        query = (
            select(PaymentRequest)
            .options(
                selectinload(PaymentRequest.created_by),
                selectinload(PaymentRequest.processing_by),
                selectinload(PaymentRequest.paid_by),
            )
        )

        if status:
            query = query.where(PaymentRequest.status == status)

        query = query.order_by(PaymentRequest.created_at.desc())
        result = await session.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def get_pending_requests(session: AsyncSession) -> List[PaymentRequest]:
        """Получает все запросы со статусом PENDING

        Args:
            session: Сессия БД

        Returns:
            Список запросов в ожидании
        """
        return await PaymentRequestCRUD.get_all_payment_requests(session, PaymentRequestStatus.PENDING)

    @staticmethod
    async def update_payment_request(
        session: AsyncSession,
        request_id: int,
        **kwargs,
    ) -> Optional[PaymentRequest]:
        """Обновляет данные запроса на оплату

        Args:
            session: Сессия БД
            request_id: ID запроса
            **kwargs: Поля для обновления

        Returns:
            Обновленный запрос или None
        """
        payment_request = await PaymentRequestCRUD.get_payment_request_by_id(session, request_id)
        if not payment_request:
            return None

        for key, value in kwargs.items():
            if hasattr(payment_request, key):
                setattr(payment_request, key, value)

        payment_request.updated_at = datetime.utcnow()
        await session.commit()
        await session.refresh(payment_request)
        return payment_request

    @staticmethod
    async def cancel_payment_request(
        session: AsyncSession,
        request_id: int,
    ) -> Optional[PaymentRequest]:
        """Отменяет запрос на оплату

        Args:
            session: Сессия БД
            request_id: ID запроса

        Returns:
            Обновленный запрос или None
        """
        return await PaymentRequestCRUD.update_payment_request(
            session,
            request_id,
            status=PaymentRequestStatus.CANCELLED.value,
        )

    @staticmethod
    async def mark_as_paid(
        session: AsyncSession,
        request_id: int,
        paid_by_id: int,
        payment_proof_file_id: str,
        processing_by_id: Optional[int] = None,
    ) -> Optional[PaymentRequest]:
        """Отмечает запрос как оплаченный

        Args:
            session: Сессия БД
            request_id: ID запроса
            paid_by_id: ID пользователя который оплатил
            payment_proof_file_id: Telegram file_id платежки
            processing_by_id: ID пользователя который взял в работу (опционально)

        Returns:
            Обновленный запрос или None
        """
        update_data = {
            "status": PaymentRequestStatus.PAID.value,
            "paid_by_id": paid_by_id,
            "paid_at": datetime.utcnow(),
            "payment_proof_file_id": payment_proof_file_id,
        }

        # Устанавливаем processing_by только если он был передан
        if processing_by_id is not None:
            update_data["processing_by_id"] = processing_by_id

        return await PaymentRequestCRUD.update_payment_request(
            session,
            request_id,
            **update_data,
        )

    @staticmethod
    async def schedule_payment(
        session: AsyncSession,
        request_id: int,
        processing_by_id: int,
        scheduled_date: Optional[date] = None,
        is_today: bool = False,
    ) -> Optional[PaymentRequest]:
        """Планирует оплату на дату

        Args:
            session: Сессия БД
            request_id: ID запроса
            processing_by_id: ID пользователя который взял в работу
            scheduled_date: Запланированная дата (если не today)
            is_today: Флаг "оплачу сегодня"

        Returns:
            Обновленный запрос или None
        """
        status = PaymentRequestStatus.SCHEDULED_TODAY.value if is_today else PaymentRequestStatus.SCHEDULED_DATE.value

        return await PaymentRequestCRUD.update_payment_request(
            session,
            request_id,
            status=status,
            processing_by_id=processing_by_id,
            scheduled_date=scheduled_date,
        )

    @staticmethod
    async def set_worker_message_id(
        session: AsyncSession,
        request_id: int,
        message_id: int,
    ) -> Optional[PaymentRequest]:
        """Сохраняет ID сообщения у Worker

        Args:
            session: Сессия БД
            request_id: ID запроса
            message_id: Telegram message ID

        Returns:
            Обновленный запрос или None
        """
        return await PaymentRequestCRUD.update_payment_request(
            session,
            request_id,
            worker_message_id=message_id,
        )

    @staticmethod
    async def set_billing_message_id(
        session: AsyncSession,
        request_id: int,
        message_id: int,
    ) -> Optional[PaymentRequest]:
        """Сохраняет ID сообщения у billing контакта

        Args:
            session: Сессия БД
            request_id: ID запроса
            message_id: Telegram message ID

        Returns:
            Обновленный запрос или None
        """
        return await PaymentRequestCRUD.update_payment_request(
            session,
            request_id,
            billing_message_id=message_id,
        )


class BillingNotificationCRUD:
    """CRUD операции для работы с уведомлениями billing контактов"""

    @staticmethod
    async def create_billing_notification(
        session: AsyncSession,
        payment_request_id: int,
        billing_user_id: int,
        message_id: int,
        chat_id: int,
    ) -> BillingNotification:
        """Создает уведомление для billing контакта

        Args:
            session: Сессия БД
            payment_request_id: ID запроса на оплату
            billing_user_id: ID billing контакта
            message_id: Telegram message ID
            chat_id: Telegram chat ID

        Returns:
            Созданное уведомление
        """
        notification = BillingNotification(
            payment_request_id=payment_request_id,
            billing_user_id=billing_user_id,
            message_id=message_id,
            chat_id=chat_id,
        )
        session.add(notification)
        await session.commit()
        await session.refresh(notification)
        return notification

    @staticmethod
    async def get_billing_notifications(
        session: AsyncSession,
        payment_request_id: int,
    ) -> List[BillingNotification]:
        """Получает все уведомления для запроса на оплату

        Args:
            session: Сессия БД
            payment_request_id: ID запроса на оплату

        Returns:
            Список уведомлений с загруженными billing_user
        """
        query = (
            select(BillingNotification)
            .options(selectinload(BillingNotification.billing_user))
            .where(BillingNotification.payment_request_id == payment_request_id)
        )
        result = await session.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def delete_billing_notifications(
        session: AsyncSession,
        payment_request_id: int,
    ) -> bool:
        """Удаляет все уведомления для запроса на оплату

        Args:
            session: Сессия БД
            payment_request_id: ID запроса на оплату

        Returns:
            True если уведомления были удалены
        """
        notifications = await BillingNotificationCRUD.get_billing_notifications(session, payment_request_id)

        for notification in notifications:
            await session.delete(notification)

        await session.commit()
        return True
