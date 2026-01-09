"""Card компоненты и статусы"""

from typing import Optional
from datetime import datetime
from fasthtml.common import *
from bot.database.models import PaymentRequest, PaymentRequestStatus


def status_badge(status: PaymentRequestStatus) -> Span:
    """Бейдж статуса запроса на оплату"""
    status_config = {
        PaymentRequestStatus.PENDING: ("⏳ Ожидает", "badge-warning badge-outline opacity-80"),
        PaymentRequestStatus.SCHEDULED_TODAY: ("🔜 Сегодня", "badge-info badge-outline opacity-80"),
        PaymentRequestStatus.SCHEDULED_DATE: ("📅 Запланировано", "badge-info badge-outline opacity-80"),
        PaymentRequestStatus.PAID: ("✅ Оплачено", "badge-success badge-outline opacity-80"),
        PaymentRequestStatus.CANCELLED: ("❌ Отменено", "badge-error badge-outline opacity-80"),
    }

    # Преобразуем строку в enum если нужно
    if isinstance(status, str):
        status = PaymentRequestStatus(status)

    text, badge_class = status_config.get(status, ("Unknown", "badge-ghost"))
    return Span(text, cls=f"badge {badge_class}")


def stat_item(title: str, value: str, icon: str = "📊") -> Div:
    """Элемент статистики для stats контейнера"""
    return Div(
        Div(f"{icon} {title}", cls="stat-title"),
        Div(value, cls="stat-value"),
        cls="stat"
    )


def card(title: str, *content) -> Div:
    """Card компонент по образцу из template.py"""
    return Div(
        Div(
            H2(title, cls="card-title"),
            *content,
            cls="card-body"
        ),
        cls="card bg-base-100 shadow-xl"
    )


def format_amount_display(amount: str) -> str:
    """Форматирует сумму с разделителями разрядов"""
    import re
    clean_amount = re.sub(r'[^\d.,]', '', str(amount))
    clean_amount = clean_amount.replace(',', '.')
    parts = clean_amount.split('.')
    integer_part = parts[0] if parts else ''
    decimal_part = parts[1] if len(parts) > 1 else None

    formatted_integer = ''
    for i, digit in enumerate(reversed(integer_part)):
        if i > 0 and i % 3 == 0:
            formatted_integer = ' ' + formatted_integer
        formatted_integer = digit + formatted_integer

    if decimal_part is not None:
        return f"{formatted_integer}.{decimal_part}"
    return formatted_integer


def payment_request_detail(payment_request: PaymentRequest, can_edit: bool = False) -> Div:
    """Детальная информация о запросе на оплату"""
    # Формируем информацию о датах
    created_date = payment_request.created_at.strftime("%d.%m.%Y %H:%M") if payment_request.created_at else "-"
    paid_date = payment_request.paid_at.strftime("%d.%m.%Y %H:%M") if payment_request.paid_at else "-"
    scheduled_date = payment_request.scheduled_date.strftime("%d.%m.%Y") if payment_request.scheduled_date else "-"

    # Кнопки для файлов
    invoice_btn = (
        A(
            "📥 Скачать счёт",
            href=f"/payment/{payment_request.id}/download/invoice",
            cls="btn btn-sm btn-outline w-full"
        ) if payment_request.invoice_file_id else Div(
            Span("📄 Счёт", cls="font-medium"),
            Span("Не загружен", cls="text-gray-400 text-sm"),
            cls="flex flex-col items-center p-3 border border-dashed border-gray-300 rounded-lg"
        )
    )

    payment_proof_btn = (
        A(
            "📥 Скачать платёжку",
            href=f"/payment/{payment_request.id}/download/proof",
            cls="btn btn-sm btn-outline w-full"
        ) if payment_request.payment_proof_file_id else Div(
            Span("📄 Платёжка", cls="font-medium"),
            Span("Не загружена", cls="text-gray-400 text-sm"),
            cls="flex flex-col items-center p-3 border border-dashed border-gray-300 rounded-lg"
        )
    )

    # Кнопка назад
    back_btn = A("← Назад", href="/dashboard", cls="btn btn-ghost btn-sm")

    return Div(
        # Заголовок с кнопкой назад
        Div(
            back_btn,
            H2(f"Запрос #{payment_request.id}", cls="text-2xl font-bold"),
            cls="flex items-center gap-4 mb-6"
        ),

        # Двухколоночная структура
        Div(
            # Левая колонка - основная информация
            Div(
                Div(
                    # Название
                    Div(
                        Span("Название", cls="text-gray-500 text-sm"),
                        P(payment_request.title, cls="font-medium"),
                        cls="mb-4"
                    ),
                    # Сумма
                    Div(
                        Span("Сумма", cls="text-gray-500 text-sm"),
                        P(f"{format_amount_display(payment_request.amount)} ₽", cls="text-2xl font-bold text-primary"),
                        cls="mb-4"
                    ),
                    # Статус
                    Div(
                        Span("Статус", cls="text-gray-500 text-sm"),
                        Div(status_badge(payment_request.status), cls="mt-1"),
                        cls="mb-4"
                    ),
                    # Даты
                    Div(
                        Span("Создано", cls="text-gray-500 text-sm"),
                        P(created_date, cls="font-medium"),
                        cls="mb-4"
                    ),
                    Div(
                        Span("Создатель", cls="text-gray-500 text-sm"),
                        P(payment_request.created_by.display_name if payment_request.created_by else "-", cls="font-medium"),
                        cls="mb-4"
                    ),
                    Div(
                        Span("Оплачено", cls="text-gray-500 text-sm"),
                        P(paid_date, cls="font-medium"),
                        cls="mb-4"
                    ) if payment_request.paid_at else None,
                    Div(
                        Span("Оплатил", cls="text-gray-500 text-sm"),
                        P(payment_request.paid_by.display_name if payment_request.paid_by else "-", cls="font-medium"),
                        cls="mb-4"
                    ) if payment_request.paid_by else None,
                    Div(
                        Span("Запланировано", cls="text-gray-500 text-sm"),
                        P(scheduled_date, cls="font-medium"),
                        cls="mb-4"
                    ) if payment_request.scheduled_date else None,
                    cls="card-body"
                ),
                cls="card bg-base-100 shadow-xl"
            ),

            # Правая колонка - комментарий и файлы
            Div(
                Div(
                    # Комментарий
                    Div(
                        Span("Комментарий", cls="text-gray-500 text-sm"),
                        P(
                            payment_request.comment or "Нет комментария",
                            cls="mt-2 p-4 bg-base-200 rounded-lg whitespace-pre-wrap"
                        ),
                        cls="mb-6"
                    ),
                    # Файлы
                    Div(
                        Span("Документы", cls="text-gray-500 text-sm"),
                        Div(
                            invoice_btn,
                            payment_proof_btn,
                            cls="mt-2 flex flex-col gap-3"
                        ),
                        cls=""
                    ),
                    cls="card-body"
                ),
                cls="card bg-base-100 shadow-xl"
            ),

            cls="grid grid-cols-1 md:grid-cols-2 gap-6"
        ),

        cls=""
    )
