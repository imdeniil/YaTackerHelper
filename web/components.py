"""UI компоненты для FastHTML приложения"""

from typing import List, Optional
from datetime import datetime
from fasthtml.common import *
from bot.database.models import PaymentRequest, PaymentRequestStatus, User, UserRole


def status_badge(status: PaymentRequestStatus) -> Div:
    """Бейдж статуса запроса на оплату"""
    status_config = {
        PaymentRequestStatus.PENDING: ("⏳ Ожидает", "badge-warning"),
        PaymentRequestStatus.SCHEDULED_TODAY: ("🔜 Сегодня", "badge-info"),
        PaymentRequestStatus.SCHEDULED_DATE: ("📅 Запланировано", "badge-info"),
        PaymentRequestStatus.PAID: ("✅ Оплачено", "badge-success"),
        PaymentRequestStatus.CANCELLED: ("❌ Отменено", "badge-error"),
    }

    # Преобразуем строку в enum если нужно
    if isinstance(status, str):
        status = PaymentRequestStatus(status)

    text, badge_class = status_config.get(status, ("Unknown", "badge-ghost"))
    return Span(text, cls=f"badge {badge_class}")


def stat_card(title: str, value: str, icon: str = "📊", color: str = "bg-base-100") -> Div:
    """Карточка статистики"""
    return Div(
        Div(
            Div(
                Span(icon, cls="text-3xl"),
                cls="mb-2"
            ),
            H3(value, cls="text-3xl font-bold"),
            P(title, cls="text-sm text-gray-600"),
            cls="card-body items-center text-center"
        ),
        cls=f"card {color} shadow-xl"
    )


def navbar(display_name: str, role: str) -> Div:
    """Навигационная панель"""
    return Div(
        Div(
            Div(
                A("YaTackerHelper", href="/dashboard", cls="btn btn-ghost text-xl"),
                cls="flex-1"
            ),
            Div(
                Div(
                    Div(tabindex="0", role="button", cls="btn btn-ghost btn-circle avatar placeholder")(
                        Div(cls="bg-neutral text-neutral-content rounded-full w-10")(
                            Span(display_name[0] if display_name else "?")
                        )
                    ),
                    Ul(
                        tabindex="0",
                        cls="menu menu-sm dropdown-content mt-3 z-[1] p-2 shadow bg-base-100 rounded-box w-52"
                    )(
                        Li()(A(f"👤 {display_name}")),
                        Li()(A(f"🎭 {role.upper()}")),
                        Li()(A("🚪 Выйти", href="/logout"))
                    ),
                    cls="dropdown dropdown-end"
                ),
                cls="flex-none"
            ),
            cls="navbar bg-base-100 shadow-lg mb-6"
        ),
    )


def payment_request_row(request: PaymentRequest, show_creator: bool = False) -> Any:
    """Строка таблицы запроса на оплату"""
    created_date = request.created_at.strftime("%d.%m.%Y %H:%M")

    # Формируем строку создателя если нужно
    creator_cell = Td(request.created_by.display_name, cls="font-medium") if show_creator else None

    # Формируем дату оплаты или планируемую дату
    date_info = ""
    if request.paid_at:
        date_info = request.paid_at.strftime("%d.%m.%Y %H:%M")
    elif request.scheduled_date:
        date_info = request.scheduled_date.strftime("%d.%m.%Y")

    return Tr(
        Td(f"#{request.id}"),
        creator_cell,
        Td(request.title),
        Td(f"{request.amount} ₽", cls="font-semibold"),
        Td(status_badge(request.status)),
        Td(created_date, cls="text-sm text-gray-600"),
        Td(date_info, cls="text-sm text-gray-600") if date_info else Td("-"),
        Td(
            A("Подробнее", href=f"/payment/{request.id}", cls="btn btn-sm btn-ghost")
        )
    )


def payment_request_table(requests: List[PaymentRequest], show_creator: bool = False) -> Div:
    """Таблица запросов на оплату"""
    if not requests:
        return Div(
            Div(
                H3("📭 Нет запросов", cls="text-xl font-bold text-center text-gray-500"),
                P("Здесь будут отображаться запросы на оплату", cls="text-center text-gray-400 mt-2"),
                cls="card-body items-center"
            ),
            cls="card bg-base-100 shadow-xl"
        )

    # Заголовок с колонкой создателя если нужно
    creator_header = Th("Создатель") if show_creator else None

    return Div(
        Table(
            Thead(
                Tr(
                    Th("ID"),
                    creator_header,
                    Th("Название"),
                    Th("Сумма"),
                    Th("Статус"),
                    Th("Создано"),
                    Th("Дата оплаты"),
                    Th("Действия")
                )
            ),
            Tbody(
                *[payment_request_row(req, show_creator) for req in requests]
            ),
            cls="table table-zebra"
        ),
        cls="overflow-x-auto"
    )


def create_payment_form() -> Div:
    """Форма создания запроса на оплату"""
    return Div(
        Div(
            Form(
                H2("💰 Создать запрос на оплату", cls="card-title mb-4"),

                # Название
                Div(
                    Label("Название для плательщика", cls="label"),
                    Input(
                        type_="text",
                        name="title",
                        placeholder="Например: Оплата за услуги",
                        required=True,
                        cls="input input-bordered w-full"
                    ),
                    cls="form-control mb-4"
                ),

                # Сумма
                Div(
                    Label("Сумма (₽)", cls="label"),
                    Input(
                        type_="text",
                        name="amount",
                        placeholder="Например: 50000",
                        required=True,
                        cls="input input-bordered w-full"
                    ),
                    cls="form-control mb-4"
                ),

                # Комментарий
                Div(
                    Label("Комментарий", cls="label"),
                    Textarea(
                        name="comment",
                        placeholder="Дополнительная информация о платеже...",
                        required=True,
                        rows=3,
                        cls="textarea textarea-bordered w-full"
                    ),
                    cls="form-control mb-4"
                ),

                # Кнопка отправки
                Button(
                    "✅ Создать запрос",
                    type_="submit",
                    cls="btn btn-primary w-full"
                ),

                method="POST",
                action="/payment/create",
                cls="card-body"
            ),
            cls="card bg-base-100 shadow-xl"
        ),
    )


def user_row(user: User) -> Any:
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
        Td(f"#{user.id}"),
        Td(user.display_name, cls="font-medium"),
        Td(f"@{user.telegram_username}"),
        Td(Span(role.value.upper(), cls=f"badge {badge_color}")),
        Td("✅ Да" if user.is_billing_contact else "❌ Нет"),
        Td(user.created_at.strftime("%d.%m.%Y"), cls="text-sm text-gray-600"),
        Td(
            Div(
                A("✏️", href=f"/users/{user.id}/edit", cls="btn btn-sm btn-ghost", title="Редактировать"),
                A("🗑️", href=f"/users/{user.id}/delete", cls="btn btn-sm btn-ghost text-error", title="Удалить"),
                cls="flex gap-1"
            )
        )
    )


def user_table(users: List[User]) -> Div:
    """Таблица пользователей"""
    if not users:
        return Div(
            Div(
                H3("👥 Нет пользователей", cls="text-xl font-bold text-center text-gray-500"),
                cls="card-body items-center"
            ),
            cls="card bg-base-100 shadow-xl"
        )

    return Div(
        Table(
            Thead(
                Tr(
                    Th("ID"),
                    Th("ФИО"),
                    Th("Username"),
                    Th("Роль"),
                    Th("Billing Contact"),
                    Th("Создан"),
                    Th("Действия")
                )
            ),
            Tbody(
                *[user_row(user) for user in users]
            ),
            cls="table table-zebra"
        ),
        cls="overflow-x-auto"
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
                cls="container mx-auto p-6"
            ),
            data_theme="light"
        )
    )


def filter_tabs(current_filter: str = "all") -> Div:
    """Вкладки фильтра статусов"""
    tabs = [
        ("all", "🔍 Все"),
        ("pending", "⏳ Ожидает"),
        ("scheduled", "📅 Запланировано"),
        ("paid", "✅ Оплачено"),
        ("cancelled", "❌ Отменено"),
    ]

    tab_items = []
    for tab_id, tab_label in tabs:
        active_class = "tab-active" if tab_id == current_filter else ""
        tab_items.append(
            A(
                tab_label,
                href=f"/dashboard?filter={tab_id}",
                cls=f"tab tab-bordered {active_class}"
            )
        )

    return Div(
        Div(*tab_items, cls="tabs tabs-bordered mb-6"),
        role="tablist"
    )
