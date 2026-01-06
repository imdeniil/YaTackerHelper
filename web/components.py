"""UI компоненты для FastHTML приложения"""

from typing import List, Optional
from datetime import datetime
from fasthtml.common import *
from bot.database.models import PaymentRequest, PaymentRequestStatus, User, UserRole


def status_badge(status: PaymentRequestStatus) -> Span:
    """Бейдж статуса запроса на оплату"""
    status_config = {
        PaymentRequestStatus.PENDING: ("Ожидает", "badge-warning"),
        PaymentRequestStatus.SCHEDULED_TODAY: ("Сегодня", "badge-info"),
        PaymentRequestStatus.SCHEDULED_DATE: ("Запланировано", "badge-info"),
        PaymentRequestStatus.PAID: ("Оплачено", "badge-success"),
        PaymentRequestStatus.CANCELLED: ("Отменено", "badge-ghost"),
    }

    # Преобразуем строку в enum если нужно
    if isinstance(status, str):
        status = PaymentRequestStatus(status)

    text, badge_class = status_config.get(status, ("Unknown", "badge-ghost"))
    return Span(text, cls=f"badge {badge_class} badge-sm")


def stats_group(stats_data: List[tuple]) -> Div:
    """Группа статистики в стиле DaisyUI

    Args:
        stats_data: List of tuples (title, value, desc)
    """
    stat_items = []
    for title, value, desc in stats_data:
        stat_items.append(
            Div(
                Div(title, cls="stat-title"),
                Div(value, cls="stat-value text-primary"),
                Div(desc, cls="stat-desc") if desc else None,
                cls="stat place-items-center"
            )
        )

    return Div(
        *stat_items,
        cls="stats shadow bg-base-100 w-full stats-vertical lg:stats-horizontal"
    )


def navbar(display_name: str, role: str) -> Div:
    """Навигационная панель"""
    return Div(
        Div(
            A("YaTackerHelper", href="/dashboard", cls="btn btn-ghost text-xl"),
            cls="flex-1"
        ),
        Div(
            Div(
                Div(
                    tabindex="0",
                    role="button",
                    cls="btn btn-ghost btn-circle avatar placeholder"
                )(
                    Div(cls="bg-neutral text-neutral-content rounded-full w-10")(
                        Span(display_name[0] if display_name else "?", cls="text-lg")
                    )
                ),
                Ul(
                    tabindex="0",
                    cls="menu menu-sm dropdown-content bg-base-100 rounded-box z-[1] mt-3 w-52 p-2 shadow"
                )(
                    Li()(A(display_name, cls="font-medium")),
                    Li()(A(role.upper(), cls="text-xs opacity-60")),
                    Li(cls="border-t mt-2 pt-2")(A("Выйти", href="/logout"))
                ),
                cls="dropdown dropdown-end"
            ),
            cls="flex-none"
        ),
        cls="navbar bg-base-100 shadow-sm sticky top-0 z-10 mb-6"
    )


def payment_request_row(request: PaymentRequest, show_creator: bool = False) -> Tr:
    """Строка таблицы запроса на оплату"""
    created_date = request.created_at.strftime("%d.%m.%Y")

    # Формируем строку создателя если нужно
    creator_cell = Td(
        Div(
            Div(request.created_by.display_name, cls="font-medium"),
            Div(f"@{request.created_by.telegram_username}", cls="text-xs opacity-50"),
            cls="flex flex-col"
        )
    ) if show_creator else None

    # Формируем дату оплаты или планируемую дату
    date_info = ""
    if request.paid_at:
        date_info = request.paid_at.strftime("%d.%m.%Y")
    elif request.scheduled_date:
        date_info = request.scheduled_date.strftime("%d.%m.%Y")

    cells = [
        Td(f"#{request.id}", cls="font-mono text-sm"),
        creator_cell,
        Td(
            Div(request.title, cls="font-medium"),
            Div(request.comment[:50] + "..." if len(request.comment) > 50 else request.comment,
                cls="text-xs opacity-50 mt-1") if request.comment else None
        ),
        Td(f"{request.amount} ₽", cls="font-semibold whitespace-nowrap"),
        Td(status_badge(request.status)),
        Td(created_date, cls="text-sm"),
        Td(date_info if date_info else Span("—", cls="opacity-30"), cls="text-sm"),
        Td(
            A("Детали →", href=f"/payment/{request.id}", cls="btn btn-ghost btn-xs")
        )
    ]

    # Убираем None элементы
    return Tr(*[cell for cell in cells if cell is not None])


def payment_request_table(requests: List[PaymentRequest], show_creator: bool = False) -> Div:
    """Таблица запросов на оплату"""
    if not requests:
        return Div(
            Div(
                Div(
                    Span("📭", cls="text-4xl mb-4"),
                    H3("Нет запросов", cls="text-lg font-medium"),
                    P("Здесь будут отображаться запросы на оплату", cls="text-sm opacity-60 mt-1"),
                    cls="flex flex-col items-center text-center py-12"
                ),
                cls="card-body"
            ),
            cls="card bg-base-100 shadow-sm"
        )

    # Заголовок с колонкой создателя если нужно
    headers = [
        Th("ID"),
        Th("Создатель") if show_creator else None,
        Th("Описание"),
        Th("Сумма"),
        Th("Статус"),
        Th("Создан"),
        Th("Оплата"),
        Th("")
    ]

    return Div(
        Table(
            Thead(
                Tr(*[h for h in headers if h is not None])
            ),
            Tbody(
                *[payment_request_row(req, show_creator) for req in requests]
            ),
            cls="table table-zebra"
        ),
        cls="overflow-x-auto bg-base-100 rounded-lg shadow-sm"
    )


def create_payment_form() -> Div:
    """Форма создания запроса на оплату"""
    return Div(
        Form(
            # Название
            Div(
                Label(
                    Span("Название для плательщика", cls="label-text"),
                    cls="label"
                ),
                Input(
                    type_="text",
                    name="title",
                    placeholder="Например: Оплата за услуги",
                    required=True,
                    cls="input input-bordered w-full"
                ),
                cls="form-control"
            ),

            # Сумма
            Div(
                Label(
                    Span("Сумма (₽)", cls="label-text"),
                    cls="label"
                ),
                Input(
                    type_="text",
                    name="amount",
                    placeholder="50000",
                    required=True,
                    cls="input input-bordered w-full"
                ),
                cls="form-control"
            ),

            # Комментарий
            Div(
                Label(
                    Span("Комментарий", cls="label-text"),
                    cls="label"
                ),
                Textarea(
                    name="comment",
                    placeholder="Дополнительная информация о платеже...",
                    required=True,
                    rows=3,
                    cls="textarea textarea-bordered w-full"
                ),
                cls="form-control"
            ),

            # Кнопка отправки
            Button(
                "Создать запрос",
                type_="submit",
                cls="btn btn-primary w-full mt-4"
            ),

            method="POST",
            action="/payment/create",
            cls="space-y-4"
        ),
        cls="card bg-base-100 shadow-sm p-6"
    )


def user_row(user: User) -> Tr:
    """Строка таблицы пользователя"""
    role_badge_colors = {
        UserRole.OWNER: "badge-error",
        UserRole.MANAGER: "badge-warning",
        UserRole.WORKER: "badge-info",
    }

    # Преобразуем строку в enum если нужно
    role = user.role if isinstance(user.role, UserRole) else UserRole(user.role)
    badge_color = role_badge_colors.get(role, "badge-ghost")

    return Tr(
        Td(f"#{user.id}", cls="font-mono text-sm"),
        Td(
            Div(
                Div(user.display_name, cls="font-medium"),
                Div(f"@{user.telegram_username}", cls="text-xs opacity-50"),
                cls="flex flex-col"
            )
        ),
        Td(Span(role.value.upper(), cls=f"badge {badge_color} badge-sm")),
        Td(
            Span("Да", cls="badge badge-success badge-sm") if user.is_billing_contact
            else Span("Нет", cls="opacity-30")
        ),
        Td(user.created_at.strftime("%d.%m.%Y"), cls="text-sm"),
        Td(
            Div(
                A("Изменить", href=f"/users/{user.id}/edit", cls="btn btn-ghost btn-xs"),
                cls="flex gap-1"
            )
        )
    )


def user_table(users: List[User]) -> Div:
    """Таблица пользователей"""
    if not users:
        return Div(
            Div(
                Div(
                    Span("👥", cls="text-4xl mb-4"),
                    H3("Нет пользователей", cls="text-lg font-medium"),
                    cls="flex flex-col items-center text-center py-12"
                ),
                cls="card-body"
            ),
            cls="card bg-base-100 shadow-sm"
        )

    return Div(
        Table(
            Thead(
                Tr(
                    Th("ID"),
                    Th("Пользователь"),
                    Th("Роль"),
                    Th("Billing"),
                    Th("Создан"),
                    Th("")
                )
            ),
            Tbody(
                *[user_row(user) for user in users]
            ),
            cls="table table-zebra"
        ),
        cls="overflow-x-auto bg-base-100 rounded-lg shadow-sm"
    )


def page_layout(title: str, content: Any, user_name: str, role: str) -> Html:
    """Общий layout для страниц дашборда"""
    return Html(
        Head(
            Title(f"{title} - YaTackerHelper"),
            Meta(charset="utf-8"),
            Meta(name="viewport", content="width=device-width, initial-scale=1"),
        ),
        Body(
            navbar(user_name, role),
            Div(
                content,
                cls="container mx-auto px-4 pb-8 max-w-7xl"
            ),
            data_theme="light",
            cls="bg-base-200 min-h-screen"
        )
    )


def filter_tabs(current_filter: str = "all") -> Div:
    """Вкладки фильтра статусов"""
    tabs = [
        ("all", "Все"),
        ("pending", "Ожидает"),
        ("scheduled", "Запланировано"),
        ("paid", "Оплачено"),
        ("cancelled", "Отменено"),
    ]

    tab_items = []
    for tab_id, tab_label in tabs:
        active_class = "tab-active" if tab_id == current_filter else ""
        tab_items.append(
            A(
                tab_label,
                href=f"/dashboard?filter={tab_id}",
                cls=f"tab tab-lifted {active_class}"
            )
        )

    return Div(
        *tab_items,
        role="tablist",
        cls="tabs tabs-lifted mb-4"
    )
