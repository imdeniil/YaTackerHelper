from datetime import datetime
from enum import Enum
from sqlalchemy import Column, Integer, BigInteger, String, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class UserRole(str, Enum):
    """Роли пользователей в системе"""
    OWNER = "owner"
    MANAGER = "manager"
    WORKER = "worker"


class User(Base):
    """Модель пользователя бота

    Attributes:
        id: Внутренний ID пользователя
        telegram_id: ID пользователя в Telegram (заполняется при первом входе)
        telegram_username: Username в Telegram (используется для создания)
        tracker_login: Логин пользователя в Yandex Tracker
        display_name: ФИО пользователя из Tracker (для отображения)
        role: Роль пользователя (owner/manager/worker)
        created_at: Дата создания записи
        settings: Связь 1:1 с настройками пользователя
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id = Column(BigInteger, unique=True, nullable=True, index=True)
    telegram_username = Column(String, unique=True, nullable=False, index=True)
    tracker_login = Column(String, nullable=False)
    display_name = Column(String, nullable=False)
    role = Column(SQLEnum(UserRole), nullable=False, default=UserRole.WORKER)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    settings = relationship("UserSettings", back_populates="user", uselist=False, cascade="all, delete-orphan")

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
