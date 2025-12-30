"""Хэндлеры бота."""

from .commands import router as commands_router
from .payment_callbacks import payment_callbacks_router

__all__ = ["commands_router", "payment_callbacks_router"]
