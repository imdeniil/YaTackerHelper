"""UI компоненты для FastHTML приложения"""

from typing import List, Optional
from datetime import datetime
from fasthtml.common import *
from bot.database.models import PaymentRequest, PaymentRequestStatus, User, UserRole


def status_badge(status: PaymentRequestStatus) -> Div:
    """Бейдж статуса запроса на оплату с улучшенным дизайном"""
    status_config = {
        PaymentRequestStatus.PENDING: ("⏳ Ожидает", "badge-warning", "font-semibold"),
        PaymentRequestStatus.SCHEDULED_TODAY: ("🔜 Сегодня", "badge-info", "font-semibold"),
        PaymentRequestStatus.SCHEDULED_DATE: ("📅 Запланировано", "badge-info", "font-semibold"),
        PaymentRequestStatus.PAID: ("✅ Оплачено", "badge-success", "font-semibold"),
        PaymentRequestStatus.CANCELLED: ("❌ Отменено", "badge-error", "font-semibold"),
    }

    # Преобразуем строку в enum если нужно
    if isinstance(status, str):
        status = PaymentRequestStatus(status)

    text, badge_class, font_class = status_config.get(status, ("Unknown", "badge-ghost", ""))
    return Span(text, cls=f"badge {badge_class} {font_class} badge-lg")


def stat_card(title: str, value: str, icon: str = "📊", color: str = "bg-base-100", accent_color: str = "primary") -> Div:
    """Карточка статистики с улучшенным дизайном"""
    return Div(
        Div(
            Div(
                # Иконка в цветном круге
                Div(
                    Span(icon, cls="text-2xl"),
                    cls=f"w-12 h-12 rounded-full bg-{accent_color} bg-opacity-10 flex items-center justify-center mb-3"
                ),
                # Значение
                H2(value, cls="text-4xl font-bold mb-1"),
                # Название
                P(title, cls="text-sm text-gray-500 uppercase tracking-wide"),
                cls="flex flex-col items-start"
            ),
            cls="card-body"
        ),
        cls=f"card {color} shadow-lg hover:shadow-xl transition-shadow border border-gray-100"
    )


def navbar(display_name: str, role: str) -> Div:
    """Навигационная панель с улучшенным дизайном"""
    # Определяем цвет роли
    role_colors = {
        "owner": "badge-error",
        "manager": "badge-warning",
        "worker": "badge-info"
    }
    role_badge_class = role_colors.get(role.lower(), "badge-ghost")

    return Div(
        Div(
            # Логотип
            Div(
                A(
                    Span("💼", cls="text-2xl mr-2"),
                    Span("YaTackerHelper", cls="font-bold text-xl"),
                    href="/dashboard",
                    cls="flex items-center hover:opacity-80 transition-opacity"
                ),
                cls="flex-1"
            ),

            # Профиль
            Div(
                Div(
                    # Кнопка аватара
                    Div(
                        tabindex="0",
                        role="button",
                        cls="btn btn-ghost gap-2 hover:bg-gray-100"
                    )(
                        Div(cls="avatar placeholder")(
                            Div(cls="bg-primary text-primary-content rounded-full w-10")(
                                Span(display_name[0] if display_name else "?", cls="text-lg font-bold")
                            )
                        ),
                        Div(cls="flex flex-col items-start")(
                            Span(display_name, cls="font-medium text-sm"),
                            Span(role.upper(), cls=f"badge {role_badge_class} badge-xs")
                        )
                    ),

                    # Выпадающее меню
                    Ul(
                        tabindex="0",
                        cls="menu menu-sm dropdown-content mt-3 z-[1] p-2 shadow-lg bg-base-100 rounded-box w-52 border border-gray-200"
                    )(
                        Li(cls="menu-title")(
                            Span("Профиль")
                        ),
                        Li()(
                            A(
                                Span("👤 ", cls="mr-2"),
                                display_name,
                                cls="font-medium"
                            )
                        ),
                        Li()(
                            A(
                                Span("🎭 ", cls="mr-2"),
                                f"Роль: {role.upper()}"
                            )
                        ),
                        Li(cls="border-t border-gray-200 mt-2 pt-2")(
                            A(
                                Span("🚪 ", cls="mr-2"),
                                "Выйти",
                                href="/logout",
                                cls="text-error hover:bg-error hover:text-white"
                            )
                        )
                    ),
                    cls="dropdown dropdown-end"
                ),
                cls="flex-none"
            ),
            cls="navbar bg-white shadow-md border-b border-gray-200 px-4 py-3"
        ),
    )


def payment_request_row(request: PaymentRequest, show_creator: bool = False) -> Any:
    """Строка таблицы запроса на оплату с улучшенным дизайном"""
    created_date = request.created_at.strftime("%d.%m.%Y %H:%M")

    # Формируем строку создателя если нужно
    creator_cell = Td(
        Div(
            Span(request.created_by.display_name, cls="font-medium"),
            cls="flex items-center"
        )
    ) if show_creator else None

    # Формируем дату оплаты или планируемую дату
    date_info = ""
    if request.paid_at:
        date_info = request.paid_at.strftime("%d.%m.%Y %H:%M")
    elif request.scheduled_date:
        date_info = request.scheduled_date.strftime("%d.%m.%Y")

    return Tr(
        Td(
            Span(f"#{request.id}", cls="badge badge-ghost badge-sm"),
        ),
        creator_cell,
        Td(
            Div(
                Span(request.title, cls="font-medium text-gray-800"),
                cls="max-w-xs truncate"
            )
        ),
        Td(
            Span(f"{request.amount} ₽", cls="font-bold text-lg")
        ),
        Td(status_badge(request.status)),
        Td(
            Span(created_date, cls="text-sm text-gray-500")
        ),
        Td(
            Span(date_info, cls="text-sm text-gray-500") if date_info else Span("-", cls="text-gray-400")
        ),
        Td(
            A(
                "👁️ Подробнее",
                href=f"/payment/{request.id}",
                cls="btn btn-sm btn-outline btn-primary hover:btn-primary"
            )
        ),
        cls="hover:bg-gray-50 transition-colors"
    )


def payment_request_table(requests: List[PaymentRequest], show_creator: bool = False) -> Div:
    """Таблица запросов на оплату"""
    if not requests:
        return Div(
            Div(
                Div(
                    Span("📭", cls="text-6xl mb-4"),
                    H3("Нет запросов", cls="text-2xl font-bold text-gray-700 mb-2"),
                    P("Здесь будут отображаться запросы на оплату", cls="text-gray-500"),
                    cls="flex flex-col items-center py-12"
                ),
            ),
            cls="card bg-base-100 shadow-lg border border-gray-100"
        )

    # Заголовок с колонкой создателя если нужно
    creator_header = Th("Создатель", cls="bg-gray-50") if show_creator else None

    return Div(
        Div(
            Table(
                Thead(
                    Tr(
                        Th("ID", cls="bg-gray-50"),
                        creator_header,
                        Th("Название", cls="bg-gray-50"),
                        Th("Сумма", cls="bg-gray-50"),
                        Th("Статус", cls="bg-gray-50"),
                        Th("Создано", cls="bg-gray-50"),
                        Th("Дата оплаты", cls="bg-gray-50"),
                        Th("Действия", cls="bg-gray-50")
                    )
                ),
                Tbody(
                    *[payment_request_row(req, show_creator) for req in requests]
                ),
                cls="table table-lg"
            ),
            cls="overflow-x-auto"
        ),
        cls="card bg-base-100 shadow-lg border border-gray-100"
    )


def create_payment_form() -> Div:
    """Форма создания запроса на оплату с улучшенным дизайном"""
    return Div(
        Div(
            Form(
                Div(
                    Span("💰", cls="text-3xl"),
                    H2("Создать запрос на оплату", cls="text-2xl font-bold"),
                    cls="flex items-center gap-3 mb-6"
                ),

                # Название
                Div(
                    Label(
                        Span("Название для плательщика", cls="label-text font-medium"),
                        cls="label"
                    ),
                    Input(
                        type_="text",
                        name="title",
                        placeholder="Например: Оплата за услуги разработки",
                        required=True,
                        cls="input input-bordered w-full focus:input-primary"
                    ),
                    cls="form-control mb-4"
                ),

                # Сумма
                Div(
                    Label(
                        Span("Сумма (₽)", cls="label-text font-medium"),
                        cls="label"
                    ),
                    Input(
                        type_="text",
                        name="amount",
                        placeholder="50000",
                        required=True,
                        cls="input input-bordered w-full focus:input-primary"
                    ),
                    cls="form-control mb-4"
                ),

                # Комментарий
                Div(
                    Label(
                        Span("Комментарий", cls="label-text font-medium"),
                        cls="label"
                    ),
                    Textarea(
                        name="comment",
                        placeholder="Опишите детали платежа: за что, за какой период, дополнительные условия...",
                        required=True,
                        rows=4,
                        cls="textarea textarea-bordered w-full focus:textarea-primary"
                    ),
                    cls="form-control mb-6"
                ),

                # Кнопка отправки
                Button(
                    Span("✅ ", cls="mr-2"),
                    "Создать запрос",
                    type_="submit",
                    cls="btn btn-primary btn-lg w-full"
                ),

                method="POST",
                action="/payment/create",
                cls="card-body"
            ),
            cls="card bg-base-100 shadow-lg border border-gray-100"
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
    """Общий layout для страниц дашборда с улучшенным дизайном"""
    return Html(
        Head(
            Title(f"{title} - YaTackerHelper"),
            Meta(charset="utf-8"),
            Meta(name="viewport", content="width=device-width, initial-scale=1"),
        ),
        Body(
            # Навбар
            navbar(user_name, role),

            # Основной контент с фоном
            Div(
                Div(
                    content,
                    cls="container mx-auto px-4 py-8 max-w-7xl"
                ),
                cls="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100"
            ),
            data_theme="light"
        )
    )


def filter_tabs(current_filter: str = "all") -> Div:
    """Вкладки фильтра статусов с улучшенным дизайном"""
    tabs = [
        ("all", "🔍 Все", "primary"),
        ("pending", "⏳ Ожидает", "warning"),
        ("scheduled", "📅 Запланировано", "info"),
        ("paid", "✅ Оплачено", "success"),
        ("cancelled", "❌ Отменено", "error"),
    ]

    tab_items = []
    for tab_id, tab_label, color in tabs:
        if tab_id == current_filter:
            tab_items.append(
                A(
                    tab_label,
                    href=f"/dashboard?filter={tab_id}",
                    cls=f"btn btn-{color} btn-sm"
                )
            )
        else:
            tab_items.append(
                A(
                    tab_label,
                    href=f"/dashboard?filter={tab_id}",
                    cls=f"btn btn-outline btn-{color} btn-sm"
                )
            )

    return Div(
        Div(
            *tab_items,
            cls="flex flex-wrap gap-2 mb-6"
        ),
    )
