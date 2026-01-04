"""Диалог управления пользователями (CRUD)

Single window интерфейс с режимами:
- list: Просмотр списка пользователей
- create: Создание нового пользователя
- edit: Редактирование пользователя
- delete: Удаление пользователя
"""

from aiogram_dialog import Dialog
from .windows import user_management_window


user_management_dialog = Dialog(user_management_window)


__all__ = ["user_management_dialog"]
