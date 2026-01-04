"""Диалог настроек пользователя

Single window интерфейс для изменения настроек пользователя:
- Очередь по умолчанию
- Портфель по умолчанию
"""

from aiogram_dialog import Dialog
from .windows import user_settings_window


user_settings_dialog = Dialog(user_settings_window)


__all__ = ["user_settings_dialog"]
