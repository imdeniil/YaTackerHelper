"""Хэндлеры бота."""

from .commands import router as commands_router
from .payment_callbacks import payment_callbacks_router
from .pending_list_callbacks import pending_list_router
from .testing import testing_router

__all__ = ["commands_router", "payment_callbacks_router", "pending_list_router", "testing_router"]
