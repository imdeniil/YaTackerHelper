from datetime import datetime
from decimal import Decimal
from enum import Enum
from sqlalchemy import Column, Integer, BigInteger, String, DateTime, Boolean, Date, Numeric, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class UserRole(str, Enum):
    """Роли пользователей в системе"""
    OWNER = "owner"
    MANAGER = "manager"
    WORKER = "worker"

class PaymentRequestStatus(str, Enum):
    """Статусы запросов на оплату"""
    PENDING = "pending"              # Ожидает оплаты
    SCHEDULED_TODAY = "scheduled_today"  # Оплатят сегодня
    SCHEDULED_DATE = "scheduled_date"    # Оплатят в конкретную дату
    PAID = "paid"                    # Оплачено
    CANCELLED = "cancelled"          # Отменен

class User(Base):
    """Модель пользователя бота

    Attributes:
        id: Внутренний ID пользователя
        telegram_id: ID пользователя в Telegram (заполняется при первом входе)
        telegram_username: Username в Telegram (используется для создания)
        tracker_login: Логин пользователя в Yandex Tracker (опциональный, только для работы с Tracker)
        display_name: ФИО пользователя (для отображения)
        role: Роль пользователя (owner/manager/worker)
        is_billing_contact: Флаг контактного лица для счетов и уведомлений об оплате
        created_at: Дата создания записи
        settings: Связь 1:1 с настройками пользователя
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id = Column(BigInteger, unique=True, nullable=True, index=True)
    telegram_username = Column(String, unique=True, nullable=False, index=True)
    tracker_login = Column(String, nullable=True)
    display_name = Column(String, nullable=False)
    role = Column(SQLEnum(UserRole), nullable=False, default=UserRole.WORKER)
    is_billing_contact = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    settings = relationship("UserSettings", back_populates="user", uselist=False, cascade="all, delete-orphan")
    created_payment_requests = relationship("PaymentRequest", foreign_keys="PaymentRequest.created_by_id", back_populates="created_by")
    processing_payment_requests = relationship("PaymentRequest", foreign_keys="PaymentRequest.processing_by_id", back_populates="processing_by")
    paid_payment_requests = relationship("PaymentRequest", foreign_keys="PaymentRequest.paid_by_id", back_populates="paid_by")

    def __repr__(self):
        return f"<User(id={self.id}, telegram_id={self.telegram_id}, username={self.telegram_username}, role={self.role.value})>"


class UserSettings(Base):
    """Модель настроек пользователя

    Attributes:
        id: Внутренний ID настроек
        user_id: FK к пользователю
        default_queue: Очередь по умолчанию для копирования проектов
        default_portfolio: Портфель по умолчанию для копирования проектов
        user: Связь с пользователем
    """
    __tablename__ = "user_settings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    default_queue = Column(String, nullable=False, default="ZADACIBMT")
    default_portfolio = Column(String, nullable=False, default="65cde69d486b9524503455b7")

    # Relationships
    user = relationship("User", back_populates="settings")

    def __repr__(self):
        return f"<UserSettings(user_id={self.user_id}, queue={self.default_queue}, portfolio={self.default_portfolio})>"


class PaymentRequest(Base):
    """Модель запроса на оплату

    Attributes:
        id: Внутренний ID запроса
        created_by_id: FK пользователя-создателя (Worker)
        title: Название для плательщика
        amount: Сумма в рублях
        comment: Комментарий к запросу
        invoice_file_id: Telegram file_id счета от Worker
        status: Статус запроса
        created_at: Дата и время создания
        updated_at: Дата и время последнего обновления
        processing_by_id: FK пользователя который взял в работу (первый billing контакт)
        paid_by_id: FK пользователя который оплатил
        paid_at: Дата и время оплаты
        scheduled_date: Запланированная дата оплаты
        payment_proof_file_id: Telegram file_id платежки от billing контакта
        worker_message_id: ID сообщения у Worker для обновления
        billing_message_id: ID сообщения у billing контакта для обновления
    """
    __tablename__ = "payment_requests"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Создатель (Worker)
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String, nullable=False)
    amount = Column(String, nullable=False)  # Храним как строку для простоты
    comment = Column(String, nullable=False)
    invoice_file_id = Column(String, nullable=True)

    # Статус и даты
    status = Column(SQLEnum(PaymentRequestStatus), nullable=False, default=PaymentRequestStatus.PENDING.value, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Обработка billing контактом
    processing_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    paid_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    paid_at = Column(DateTime, nullable=True)
    scheduled_date = Column(Date, nullable=True)
    payment_proof_file_id = Column(String, nullable=True)

    # Telegram message IDs для обновления
    worker_message_id = Column(BigInteger, nullable=True)
    billing_message_id = Column(BigInteger, nullable=True)

    # Relationships
    created_by = relationship("User", foreign_keys=[created_by_id], back_populates="created_payment_requests")
    processing_by = relationship("User", foreign_keys=[processing_by_id], back_populates="processing_payment_requests")
    paid_by = relationship("User", foreign_keys=[paid_by_id], back_populates="paid_payment_requests")

    def __repr__(self):
        return f"<PaymentRequest(id={self.id}, title={self.title}, amount={self.amount}, status={self.status.value})>"
