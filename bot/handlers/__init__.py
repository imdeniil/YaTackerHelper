"""Хэндлеры бота."""

from .commands import router as commands_router
from .payments import payment_callbacks_router, pending_list_router
from .testing import testing_router

__all__ = ["commands_router", "payment_callbacks_router", "pending_list_router", "testing_router"]
