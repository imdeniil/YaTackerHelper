"""Table компоненты"""

import re
from typing import List, Optional
from fasthtml.common import *
from bot.database.models import PaymentRequest, User, UserRole
from .cards import status_badge
from .pagination import pagination_footer


def format_amount(amount: str) -> str:
    """Форматирует сумму с разделителями разрядов (пробелами)

    Args:
        amount: Сумма в виде строки

    Returns:
        Отформатированная строка с пробелами между разрядами
    """
    # Убираем существующие пробелы и другие разделители
    clean_amount = re.sub(r'[^\d.,]', '', str(amount))
    # Заменяем запятую на точку
    clean_amount = clean_amount.replace(',', '.')

    # Разделяем на целую и дробную части
    parts = clean_amount.split('.')
    integer_part = parts[0] if parts else ''
    decimal_part = parts[1] if len(parts) > 1 else None

    # Форматируем целую часть с пробелами (каждые 3 цифры с конца)
    formatted_integer = ''
    for i, digit in enumerate(reversed(integer_part)):
        if i > 0 and i % 3 == 0:
            formatted_integer = ' ' + formatted_integer
        formatted_integer = digit + formatted_integer

    # Собираем обратно
    if decimal_part is not None:
        return f"{formatted_integer}.{decimal_part}"
    return formatted_integer


def payment_request_row(request: PaymentRequest, show_creator: bool = False) -> Tr:
    """Строка таблицы запроса на оплату"""
    created_date = request.created_at.strftime("%d.%m.%Y %H:%M")

    # Формируем строку создателя если нужно
    creator_cell = Td(request.created_by.display_name) if show_creator else None

    # Формируем дату оплаты или планируемую дату
    date_info = ""
    if request.paid_at:
        date_info = request.paid_at.strftime("%d.%m.%Y %H:%M")
    elif request.scheduled_date:
        date_info = request.scheduled_date.strftime("%d.%m.%Y")

    # Иконки для счета и платежки
    invoice_icon = (
        A("📥", href=f"/payment/{request.id}/download/invoice", title="Скачать счет", cls="text-lg", onclick="event.stopPropagation()")
        if request.invoice_file_id
        else Span("❌", cls="text-lg opacity-50")
    )

    payment_proof_icon = (
        A("📥", href=f"/payment/{request.id}/download/proof", title="Скачать платежку", cls="text-lg", onclick="event.stopPropagation()")
        if request.payment_proof_file_id
        else Span("❌", cls="text-lg opacity-50")
    )

    return Tr(
        Th(str(request.id)),
        Td(request.title),
        creator_cell,
        Td(f"{format_amount(request.amount)} ₽"),
        Td(status_badge(request.status)),
        Td(invoice_icon),
        Td(payment_proof_icon),
        Td(created_date),
        Td(date_info if date_info else "-"),
        cls="hover cursor-pointer",
        onclick=f"window.location.href='/payment/{request.id}'"
    )


def payment_request_table(requests: List[PaymentRequest], show_creator: bool = False, pagination_data: Optional[dict] = None) -> Div:
    """Таблица запросов на оплату с пагинацией"""
    if not requests:
        return Div(
            P("Нет запросов", cls="text-center py-8 text-gray-500"),
            id="table-container"
        )

    # Заголовок с колонкой создателя если нужно
    creator_header = Th("Создатель") if show_creator else None

    table_content = Div(
        Table(
            Thead(
                Tr(
                    Th("ID"),
                    Th("Название"),
                    creator_header,
                    Th("Сумма"),
                    Th("Статус"),
                    Th("Счет"),
                    Th("Платежка"),
                    Th("Создано"),
                    Th("Дата оплаты")
                )
            ),
            Tbody(
                *[payment_request_row(req, show_creator) for req in requests]
            ),
            cls="table table-xs"
        ),
        cls="overflow-x-auto"
    )

    # Добавляем пагинацию если данные переданы
    if pagination_data:
        return Div(
            table_content,
            pagination_footer(
                current_page=pagination_data['current_page'],
                total_pages=pagination_data['total_pages'],
                per_page=pagination_data['per_page'],
                total_items=pagination_data['total_items'],
                filter_status=pagination_data['filter_status']
            ),
            id="table-container"
        )

    return Div(table_content, id="table-container")


def user_row(user: User) -> Tr:
    """Строка таблицы пользователя"""
    role_config = {
        UserRole.OWNER: ("badge-error badge-outline", "👑", "Владелец"),
        UserRole.MANAGER: ("badge-warning badge-outline", "📊", "Менеджер"),
        UserRole.WORKER: ("badge-info badge-outline", "👷", "Сотрудник"),
    }

    # Преобразуем строку в enum если нужно
    role = user.role if isinstance(user.role, UserRole) else UserRole(user.role)
    badge_color, role_icon, role_name = role_config.get(role, ("badge-ghost", "👤", "Неизвестно"))

    # Иконка плательщика
    billing_icon = "✅" if user.is_billing_contact else "❌"

    return Tr(
        Th(str(user.id)),
        Td(user.display_name),
        Td(f"@{user.telegram_username}" if user.telegram_username else "-"),
        Td(Span(f"{role_icon} {role_name}", cls=f"badge {badge_color}")),
        Td(billing_icon, cls="text-center"),
        Td(user.created_at.strftime("%d.%m.%Y") if user.created_at else "-"),
        cls="hover cursor-pointer",
        onclick=f"window.location.href='/users/{user.id}/edit'"
    )


def user_table(users: List[User]) -> Div:
    """Таблица пользователей"""
    if not users:
        return Div(
            P("Нет пользователей", cls="text-center py-8 text-gray-500"),
            id="users-table-container"
        )

    return Div(
        Div(
            Table(
                Thead(
                    Tr(
                        Th("ID", cls="w-1/12"),
                        Th("ФИО", cls="w-3/12"),
                        Th("Username", cls="w-2/12"),
                        Th("Роль", cls="w-2/12"),
                        Th("Плательщик", cls="w-2/12 text-center"),
                        Th("Создан", cls="w-2/12")
                    )
                ),
                Tbody(
                    *[user_row(user) for user in users]
                ),
                cls="table table-xs w-full"
            ),
            cls="overflow-x-auto"
        ),
        id="users-table-container"
    )
