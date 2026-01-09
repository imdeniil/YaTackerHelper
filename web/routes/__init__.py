"""Web routes for YaTackerHelper"""

from .auth import setup_auth_routes
from .dashboard import setup_dashboard_routes
from .payments import setup_payment_routes
from .users import setup_user_routes
from .export import setup_export_routes
from .decorators import require_auth, require_role
from .helpers import (
    format_payment_request_message,
    get_payment_keyboard,
    notify_billing_contacts_about_new_payment
)

__all__ = [
    # Route setup functions
    "setup_auth_routes",
    "setup_dashboard_routes",
    "setup_payment_routes",
    "setup_user_routes",
    "setup_export_routes",
    # Decorators
    "require_auth",
    "require_role",
    # Helpers
    "format_payment_request_message",
    "get_payment_keyboard",
    "notify_billing_contacts_about_new_payment",
]
