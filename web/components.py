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


def stat_item(title: str, value: str, icon: str = "📊") -> Div:
    """Элемент статистики для stats контейнера"""
    return Div(
        Div(f"{icon} {title}", cls="stat-title"),
        Div(value, cls="stat-value"),
        cls="stat"
    )


def navbar(display_name: str, role: str, telegram_id: Optional[int] = None) -> Div:
    """Навигационная панель с аватаром из Telegram"""
    # Получаем фото профиля из Telegram если есть telegram_id
    avatar_url = f"https://ui-avatars.com/api/?name={display_name}&background=random"

    # Пункты меню в зависимости от роли
    menu_items = [
        A("Главная", href="/dashboard", cls="btn btn-ghost")
    ]

    # Добавляем пункт Пользователи для owner
    if role.lower() == "owner":
        menu_items.append(
            A("Пользователи", href="/users", cls="btn btn-ghost")
        )

    return Div(
        Div(
            # Логотип
            Div(
                A("Система учета расходов apod-lab", href="/dashboard", cls="btn btn-ghost text-xl"),
                cls="flex-1"
            ),
            # Меню
            Div(
                *menu_items,
                cls="flex-none hidden lg:flex gap-2"
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
                            Img(src=avatar_url, alt=display_name)
                        )
                    ),
                    # Dropdown меню
                    Ul(
                        Li(A(f"👤 {display_name}", cls="justify-between")(Span(role.upper(), cls="badge"))),
                        Li(A("🚪 Выйти", href="/logout")),
                        tabindex="0",
                        cls="menu menu-sm dropdown-content mt-3 z-[1] p-2 shadow bg-base-100 rounded-box w-52"
                    ),
                    cls="dropdown dropdown-end"
                ),
                cls="flex-none"
            ),
            cls="navbar bg-base-100 shadow-lg"
        ),
        cls="mb-8"
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


def create_payment_form() -> Form:
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
        Th(str(user.id)),
        Td(user.display_name),
        Td(f"@{user.telegram_username}"),
        Td(Span(role.value.upper(), cls=f"badge {badge_color}")),
        Td("Да" if user.is_billing_contact else "Нет"),
        Td(user.created_at.strftime("%d.%m.%Y")),
        Td(
            A("Редактировать", href=f"/users/{user.id}/edit", cls="btn btn-xs btn-ghost")
        )
    )


def user_table(users: List[User]) -> Div:
    """Таблица пользователей"""
    if not users:
        return Div(
            P("Нет пользователей", cls="text-center py-8 text-gray-500")
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
            cls="table table-xs"
        ),
        cls="overflow-x-auto"
    )


def page_layout(title: str, content: Any, user_name: str, role: str, telegram_id: Optional[int] = None) -> Html:
    """Общий layout для страниц дашборда"""
    return Html(
        Head(
            Meta(charset="utf-8"),
            Meta(name="viewport", content="width=device-width, initial-scale=1"),
            Title(f"{title} - Система учета расходов apod-lab"),
            Script(src="https://cdn.tailwindcss.com"),
            Link(href="https://cdn.jsdelivr.net/npm/daisyui@4/dist/full.min.css", rel="stylesheet", type_="text/css"),
        ),
        Body(
            navbar(user_name, role, telegram_id),
            Main(
                content,
                cls="container mx-auto px-4 py-8"
            ),
            data_theme="light"
        )
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


def payment_request_detail(request: PaymentRequest, user_role: str) -> Div:
    """Детальная информация о запросе на оплату"""
    # Определяем доступные действия в зависимости от роли и статуса
    can_schedule = user_role in ["owner", "manager"] and request.status == PaymentRequestStatus.PENDING.value
    can_pay = user_role in ["owner", "manager"] and request.status in [
        PaymentRequestStatus.PENDING.value,
        PaymentRequestStatus.SCHEDULED_TODAY.value,
        PaymentRequestStatus.SCHEDULED_DATE.value
    ]
    can_cancel = request.status not in [PaymentRequestStatus.PAID.value, PaymentRequestStatus.CANCELLED.value]

    # Основная информация
    info_section = Div(
        Div(
            Div(f"ID: {request.id}", cls="text-sm opacity-70"),
            Div(f"Статус: ", status_badge(request.status), cls="flex items-center gap-2 mt-2"),
            cls="mb-4"
        ),
        Div(
            Label("Название для плательщика:", cls="font-bold"),
            P(request.title, cls="mt-1"),
            cls="mb-4"
        ),
        Div(
            Label("Сумма:", cls="font-bold"),
            P(f"{request.amount} ₽", cls="mt-1 text-2xl"),
            cls="mb-4"
        ),
        Div(
            Label("Комментарий:", cls="font-bold"),
            P(request.comment, cls="mt-1 whitespace-pre-wrap"),
            cls="mb-4"
        ),
        Div(
            Label("Создатель:", cls="font-bold"),
            P(f"{request.created_by.display_name} (@{request.created_by.telegram_username})", cls="mt-1"),
            cls="mb-4"
        ),
        Div(
            Label("Создано:", cls="font-bold"),
            P(request.created_at.strftime("%d.%m.%Y %H:%M"), cls="mt-1"),
            cls="mb-4"
        ),
    )

    # Дополнительная информация в зависимости от статуса
    if request.scheduled_date:
        info_section = Div(
            info_section,
            Div(
                Label("Запланировано на:", cls="font-bold"),
                P(request.scheduled_date.strftime("%d.%m.%Y"), cls="mt-1"),
                cls="mb-4"
            )
        )

    if request.processing_by:
        info_section = Div(
            info_section,
            Div(
                Label("Взято в работу:", cls="font-bold"),
                P(f"{request.processing_by.display_name} (@{request.processing_by.telegram_username})", cls="mt-1"),
                cls="mb-4"
            )
        )

    if request.paid_at:
        info_section = Div(
            info_section,
            Div(
                Label("Оплачено:", cls="font-bold"),
                P(request.paid_at.strftime("%d.%m.%Y %H:%M"), cls="mt-1"),
                cls="mb-4"
            )
        )

    if request.paid_by:
        info_section = Div(
            info_section,
            Div(
                Label("Оплатил:", cls="font-bold"),
                P(f"{request.paid_by.display_name} (@{request.paid_by.telegram_username})", cls="mt-1"),
                cls="mb-4"
            )
        )

    # Формы действий
    actions_section = Div()

    if can_schedule:
        actions_section = Div(
            actions_section,
            card("Запланировать оплату", schedule_payment_form(request.id))
        )

    if can_pay:
        actions_section = Div(
            actions_section,
            card("Отметить как оплаченный", mark_as_paid_form(request.id))
        )

    if can_cancel:
        actions_section = Div(
            actions_section,
            Div(
                Form(
                    Button(
                        "Отменить запрос",
                        type_="submit",
                        cls="btn btn-error w-full",
                        onclick="return confirm('Вы уверены что хотите отменить этот запрос?')"
                    ),
                    method="POST",
                    action=f"/payment/{request.id}/cancel"
                ),
                cls="mt-4"
            )
        )

    return Div(
        Div(
            A("← Назад к списку", href="/dashboard", cls="btn btn-ghost btn-sm mb-4"),
            cls="mb-4"
        ),
        card(f"Запрос на оплату #{request.id}", info_section),
        actions_section if can_schedule or can_pay or can_cancel else None
    )


def schedule_payment_form(request_id: int) -> Form:
    """Форма планирования оплаты"""
    return Form(
        # Выбор "Сегодня" или "На дату"
        Div(
            Label("Когда оплатить?", cls="label"),
            Div(
                Label(
                    Input(type_="radio", name="schedule_type", value="today", cls="radio", checked=True),
                    Span("Сегодня", cls="ml-2"),
                    cls="label cursor-pointer justify-start gap-2"
                ),
                Label(
                    Input(type_="radio", name="schedule_type", value="date", cls="radio"),
                    Span("На определенную дату", cls="ml-2"),
                    cls="label cursor-pointer justify-start gap-2"
                ),
                cls="space-y-2"
            ),
            cls="form-control mb-4"
        ),

        # Поле даты (скрывается/показывается в зависимости от выбора)
        Div(
            Label("Дата оплаты", cls="label"),
            Input(
                type_="date",
                name="scheduled_date",
                cls="input input-bordered w-full",
                id="scheduled_date_input"
            ),
            cls="form-control",
            id="date_field",
            style="display: none;"
        ),

        # Кнопка отправки
        Button(
            "Запланировать",
            type_="submit",
            cls="btn btn-primary w-full mt-4"
        ),

        # JavaScript для показа/скрытия поля даты
        Script("""
            document.querySelectorAll('input[name="schedule_type"]').forEach(radio => {
                radio.addEventListener('change', function() {
                    const dateField = document.getElementById('date_field');
                    const dateInput = document.getElementById('scheduled_date_input');
                    if (this.value === 'date') {
                        dateField.style.display = 'block';
                        dateInput.required = true;
                    } else {
                        dateField.style.display = 'none';
                        dateInput.required = false;
                    }
                });
            });
        """),

        method="POST",
        action=f"/payment/{request_id}/schedule"
    )


def mark_as_paid_form(request_id: int) -> Form:
    """Форма отметки как оплаченного (упрощенная версия без загрузки файла)"""
    return Form(
        Div(
            P("После отметки как оплаченный, запрос будет закрыт.", cls="text-sm opacity-70 mb-4"),
            P("Загрузка платежного документа будет доступна через Telegram бот.", cls="text-sm opacity-70 mb-4"),
            cls="mb-4"
        ),

        # Кнопка отправки
        Button(
            "Отметить как оплаченный",
            type_="submit",
            cls="btn btn-success w-full",
            onclick="return confirm('Вы уверены что хотите отметить этот запрос как оплаченный?')"
        ),

        method="POST",
        action=f"/payment/{request_id}/pay"
    )


def user_edit_form(user: User) -> Form:
    """Форма редактирования пользователя"""
    return Form(
        # ФИО
        Div(
            Label("ФИО", cls="label"),
            Input(
                type_="text",
                name="display_name",
                value=user.display_name,
                required=True,
                cls="input input-bordered w-full"
            ),
            cls="form-control mb-4"
        ),

        # Username
        Div(
            Label("Telegram Username (без @)", cls="label"),
            Input(
                type_="text",
                name="telegram_username",
                value=user.telegram_username,
                required=True,
                cls="input input-bordered w-full"
            ),
            cls="form-control mb-4"
        ),

        # Tracker Login
        Div(
            Label("Логин в Yandex Tracker (опционально)", cls="label"),
            Input(
                type_="text",
                name="tracker_login",
                value=user.tracker_login or "",
                cls="input input-bordered w-full"
            ),
            cls="form-control mb-4"
        ),

        # Роль
        Div(
            Label("Роль", cls="label"),
            Select(
                Option("OWNER", value=UserRole.OWNER.value, selected=user.role == UserRole.OWNER),
                Option("MANAGER", value=UserRole.MANAGER.value, selected=user.role == UserRole.MANAGER),
                Option("WORKER", value=UserRole.WORKER.value, selected=user.role == UserRole.WORKER),
                name="role",
                required=True,
                cls="select select-bordered w-full"
            ),
            cls="form-control mb-4"
        ),

        # Billing Contact
        Div(
            Label(
                Input(
                    type_="checkbox",
                    name="is_billing_contact",
                    value="true",
                    checked=user.is_billing_contact,
                    cls="checkbox"
                ),
                Span("Billing Contact", cls="ml-2"),
                cls="label cursor-pointer justify-start gap-2"
            ),
            cls="form-control mb-4"
        ),

        # Кнопки
        Div(
            Button("Сохранить", type_="submit", cls="btn btn-primary"),
            A("Отмена", href="/users", cls="btn btn-ghost"),
            cls="flex gap-2"
        ),

        method="POST",
        action=f"/users/{user.id}/edit"
    )


def user_create_form() -> Form:
    """Форма создания нового пользователя"""
    return Form(
        # ФИО
        Div(
            Label("ФИО", cls="label"),
            Input(
                type_="text",
                name="display_name",
                placeholder="Иванов Иван Иванович",
                required=True,
                cls="input input-bordered w-full"
            ),
            cls="form-control mb-4"
        ),

        # Username
        Div(
            Label("Telegram Username (без @)", cls="label"),
            Input(
                type_="text",
                name="telegram_username",
                placeholder="username",
                required=True,
                cls="input input-bordered w-full"
            ),
            cls="form-control mb-4"
        ),

        # Tracker Login
        Div(
            Label("Логин в Yandex Tracker (опционально)", cls="label"),
            Input(
                type_="text",
                name="tracker_login",
                placeholder="i.ivanov",
                cls="input input-bordered w-full"
            ),
            cls="form-control mb-4"
        ),

        # Роль
        Div(
            Label("Роль", cls="label"),
            Select(
                Option("WORKER", value=UserRole.WORKER.value, selected=True),
                Option("MANAGER", value=UserRole.MANAGER.value),
                Option("OWNER", value=UserRole.OWNER.value),
                name="role",
                required=True,
                cls="select select-bordered w-full"
            ),
            cls="form-control mb-4"
        ),

        # Billing Contact
        Div(
            Label(
                Input(
                    type_="checkbox",
                    name="is_billing_contact",
                    value="true",
                    cls="checkbox"
                ),
                Span("Billing Contact", cls="ml-2"),
                cls="label cursor-pointer justify-start gap-2"
            ),
            cls="form-control mb-4"
        ),

        # Кнопки
        Div(
            Button("Создать", type_="submit", cls="btn btn-primary"),
            A("Отмена", href="/users", cls="btn btn-ghost"),
            cls="flex gap-2"
        ),

        method="POST",
        action="/users/create"
    )
