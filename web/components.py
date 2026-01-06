"""UI компоненты для FastHTML приложения"""

from typing import List, Optional
from datetime import datetime
from fasthtml.common import *
from bot.database.models import PaymentRequest, PaymentRequestStatus, User, UserRole


def status_badge(status: PaymentRequestStatus) -> Span:
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


def stat_card(title: str, value: str, icon: str = "📊") -> Div:
    """Карточка статистики"""
    return Div(
        Div(
            H2(value, cls="card-title text-2xl"),
            P(f"{icon} {title}", cls="text-sm"),
            cls="stat"
        ),
        cls="stats shadow"
    )


def navbar(display_name: str, role: str, telegram_id: Optional[int] = None) -> Div:
    """Навигационная панель с аватаром из Telegram"""
    # Получаем фото профиля из Telegram если есть telegram_id
    # Telegram позволяет получить аватар через userpic API
    avatar_url = f"https://t.me/i/userpic/320/{telegram_id}.jpg" if telegram_id else None

    return Div(
        Div(
            # Логотип
            Div(
                A("Система учета расходов apod-lab", href="/dashboard", cls="btn btn-ghost text-xl"),
                cls="flex-1"
            ),
            # Профиль
            Div(
                Div(
                    # Аватар
                    Div(
                        tabindex="0",
                        role="button",
                        cls="btn btn-ghost btn-circle avatar"
                    )(
                        Div(cls="w-10 rounded-full")(
                            Img(
                                src=avatar_url if avatar_url else f"https://ui-avatars.com/api/?name={display_name}&background=random",
                                alt=display_name
                            )
                        )
                    ),
                    # Dropdown меню
                    Ul(
                        tabindex="0",
                        cls="menu menu-sm dropdown-content bg-base-100 rounded-box z-[1] mt-3 w-52 p-2 shadow"
                    )(
                        Li()(
                            A(
                                f"👤 {display_name}",
                                cls="justify-between"
                            )(
                                Span(role.upper(), cls="badge")
                            )
                        ),
                        Li()(A("🚪 Выйти", href="/logout"))
                    ),
                    cls="dropdown dropdown-end"
                ),
                cls="flex-none"
            ),
            cls="navbar bg-base-100"
        ),
    )


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

    return Tr(
        Th(str(request.id)),
        creator_cell,
        Td(request.title),
        Td(f"{request.amount} ₽"),
        Td(status_badge(request.status)),
        Td(created_date),
        Td(date_info if date_info else "-"),
        Td(
            A("Подробнее", href=f"/payment/{request.id}", cls="btn btn-xs btn-ghost")
        )
    )


def payment_request_table(requests: List[PaymentRequest], show_creator: bool = False) -> Div:
    """Таблица запросов на оплату"""
    if not requests:
        return Div(
            P("Нет запросов", cls="text-center py-8 text-gray-500")
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
            cls="table table-xs"
        ),
        cls="overflow-x-auto"
    )


def create_payment_form() -> Div:
    """Форма создания запроса на оплату"""
    return Form(
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
            cls="form-control"
        ),

        # Сумма
        Div(
            Label("Сумма (₽)", cls="label"),
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
            Label("Комментарий", cls="label"),
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
        action="/payment/create"
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


def page_layout(title: str, content: Any, user_name: str, role: str, telegram_id: Optional[int] = None) -> Html:
    """Общий layout для страниц дашборда"""
    return Html(
        Head(
            Title(f"{title} - Система учета расходов apod-lab"),
            Meta(charset="utf-8"),
            Meta(name="viewport", content="width=device-width, initial-scale=1"),
        ),
        Body(
            navbar(user_name, role, telegram_id),
            Div(
                content,
                cls="container mx-auto p-4"
            ),
            data_theme="light"
        )
    )


def filter_tabs(current_filter: str = "all") -> Div:
    """Фильтры статусов"""
    tabs = [
        ("all", "Все"),
        ("pending", "Ожидает"),
        ("scheduled", "Запланировано"),
        ("paid", "Оплачено"),
        ("cancelled", "Отменено"),
    ]

    tab_items = []
    for tab_id, tab_label in tabs:
        if tab_id == current_filter:
            tab_items.append(
                A(tab_label, href=f"/dashboard?filter={tab_id}", cls="btn btn-primary btn-sm")
            )
        else:
            tab_items.append(
                A(tab_label, href=f"/dashboard?filter={tab_id}", cls="btn btn-ghost btn-sm")
            )

    return Div(*tab_items, cls="flex gap-2")
