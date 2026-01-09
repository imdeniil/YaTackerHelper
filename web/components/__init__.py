"""UI компоненты для FastHTML приложения"""

from .layout import page_layout, navbar
from .tables import payment_request_table, payment_request_row, user_table, user_row
from .forms import (
    create_payment_form,
    create_payment_modal,
    user_edit_form,
    user_create_form,
    schedule_payment_form,
    mark_as_paid_form
)
from .filters import advanced_filters, filter_tabs
from .cards import card, stat_item, status_badge, payment_request_detail
from .modals import analytics_modal
from .pagination import pagination_footer, pagination_controls, per_page_selector

__all__ = [
    # Layout
    "page_layout",
    "navbar",
    # Tables
    "payment_request_table",
    "payment_request_row",
    "user_table",
    "user_row",
    # Forms
    "create_payment_form",
    "create_payment_modal",
    "user_edit_form",
    "user_create_form",
    "schedule_payment_form",
    "mark_as_paid_form",
    # Filters
    "advanced_filters",
    "filter_tabs",
    # Cards
    "card",
    "stat_item",
    "status_badge",
    "payment_request_detail",
    # Modals
    "analytics_modal",
    # Pagination
    "pagination_footer",
    "pagination_controls",
    "per_page_selector",
]
