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
            cls="btn btn-sm btn-outline"
        ) if payment_request.invoice_file_id else Span("Счёт не загружен", cls="text-gray-500")
    )

    payment_proof_btn = (
        A(
            "📥 Скачать платёжку",
            href=f"/payment/{payment_request.id}/download/proof",
            cls="btn btn-sm btn-outline"
        ) if payment_request.payment_proof_file_id else Span("Платёжка не загружена", cls="text-gray-500")
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

        # Основная информация
        Div(
            # Название и сумма
            Div(
                Div(
                    Span("Название:", cls="font-semibold"),
                    Span(payment_request.title, cls="ml-2"),
                    cls="mb-2"
                ),
                Div(
                    Span("Сумма:", cls="font-semibold"),
                    Span(f"{payment_request.amount} ₽", cls="ml-2 text-lg font-bold"),
                    cls="mb-2"
                ),
                Div(
                    Span("Статус:", cls="font-semibold"),
                    status_badge(payment_request.status),
                    cls="mb-2 flex items-center gap-2"
                ),
                cls="mb-4"
            ),

            # Комментарий
            Div(
                Span("Комментарий:", cls="font-semibold"),
                P(payment_request.comment or "Нет комментария", cls="mt-1 p-3 bg-base-200 rounded-lg"),
                cls="mb-4"
            ),

            # Даты
            Div(
                Div(
                    Span("Создано:", cls="font-semibold"),
                    Span(created_date, cls="ml-2"),
                    cls="mb-2"
                ),
                Div(
                    Span("Создатель:", cls="font-semibold"),
                    Span(payment_request.created_by.display_name if payment_request.created_by else "-", cls="ml-2"),
                    cls="mb-2"
                ),
                Div(
                    Span("Оплачено:", cls="font-semibold"),
                    Span(paid_date, cls="ml-2"),
                    cls="mb-2"
                ) if payment_request.paid_at else None,
                Div(
                    Span("Оплатил:", cls="font-semibold"),
                    Span(payment_request.paid_by.display_name if payment_request.paid_by else "-", cls="ml-2"),
                    cls="mb-2"
                ) if payment_request.paid_by else None,
                Div(
                    Span("Запланировано:", cls="font-semibold"),
                    Span(scheduled_date, cls="ml-2"),
                    cls="mb-2"
                ) if payment_request.scheduled_date else None,
                cls="mb-4"
            ),

            # Файлы
            Div(
                H3("Файлы", cls="font-semibold mb-2"),
                Div(
                    invoice_btn,
                    payment_proof_btn,
                    cls="flex gap-4"
                ),
                cls="mb-4"
            ),

            cls="card-body"
        ),

        cls="card bg-base-100 shadow-xl"
    )
