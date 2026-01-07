"""UI компоненты для FastHTML приложения"""

from typing import List, Optional
from datetime import datetime
from fasthtml.common import *
from bot.database.models import PaymentRequest, PaymentRequestStatus, User, UserRole


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


def navbar(display_name: str, role: str, avatar_url: str) -> Div:
    """Навигационная панель с аватаром из Telegram"""
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
            # Меню по левому краю
            Div(
                *menu_items,
                cls="flex-1 gap-2"
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
        Td(f"{request.amount} ₽"),
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
            P("Нет запросов", cls="text-center py-8 text-gray-500")
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
            )
        )

    return table_content


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
                    Th("Плательщик"),
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


def page_layout(title: str, content: Any, user_name: str, role: str, avatar_url: str) -> Html:
    """Общий layout для страниц дашборда"""
    return Html(
        Head(
            Meta(charset="utf-8"),
            Meta(name="viewport", content="width=device-width, initial-scale=1"),
            Title(f"{title} - Система учета расходов apod-lab"),
            Script(src="https://cdn.tailwindcss.com"),
            Link(href="https://cdn.jsdelivr.net/npm/daisyui@4/dist/full.min.css", rel="stylesheet", type_="text/css"),
            # Flatpickr для красивых календарей
            Link(href="https://cdn.jsdelivr.net/npm/flatpickr/dist/flatpickr.min.css", rel="stylesheet"),
            Script(src="https://cdn.jsdelivr.net/npm/flatpickr"),
            Script(src="https://npmcdn.com/flatpickr/dist/l10n/ru.js"),  # Русская локализация
        ),
        Body(
            navbar(user_name, role, avatar_url),
            Main(
                content,
                cls="container mx-auto px-4 py-8"
            ),
            # Инициализация Flatpickr для календарей и обновление счетчика статусов
            Script("""
                // Функция обновления счетчика выбранных статусов
                function updateStatusCount() {
                    const checkboxes = document.querySelectorAll('input[name="status"]:checked');
                    const count = checkboxes.length;
                    const summaryText = document.getElementById('status-summary-text');

                    if (summaryText) {
                        if (count > 0) {
                            summaryText.textContent = count + ' Selected';
                        } else {
                            summaryText.textContent = 'Статусы';
                        }
                    }
                }

                document.addEventListener('DOMContentLoaded', function() {
                    // Конфигурация для русской локализации и кастомного стиля
                    const config = {
                        locale: 'ru',
                        dateFormat: 'Y-m-d',
                        allowInput: true,
                        clickOpens: true,
                        theme: 'light'
                    };

                    // Инициализация календарей
                    const dateFromInput = document.getElementById('date_from_picker');
                    const dateToInput = document.getElementById('date_to_picker');

                    if (dateFromInput) {
                        flatpickr(dateFromInput, config);
                    }

                    if (dateToInput) {
                        flatpickr(dateToInput, config);
                    }
                });
            """),
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


def filter_tabs(current_filter: str = "all", per_page: int = 20) -> Div:
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
                A(tab_label, href=f"/dashboard?filter={tab_id}&page=1&per_page={per_page}", cls="btn btn-primary btn-sm")
            )
        else:
            tab_items.append(
                A(tab_label, href=f"/dashboard?filter={tab_id}&page=1&per_page={per_page}", cls="btn btn-ghost btn-sm")
            )

    return Div(*tab_items, cls="flex gap-2")


def advanced_filters(
    current_statuses: List[str] = None,
    search_query: str = "",
    date_from: str = "",
    date_to: str = "",
    amount_min: str = "",
    amount_max: str = "",
    creator_id: int = None,
    users: List = None,
    show_creator_filter: bool = False,
    per_page: int = 20
) -> Form:
    """Расширенные фильтры с множественным выбором"""
    current_statuses = current_statuses or []

    return Form(
        # Строка поиска с кнопками (на всю ширину)
        Div(
            Input(
                type="text",
                name="search",
                value=search_query,
                placeholder="🔍 Поиск по названию...",
                cls="input input-sm input-bordered flex-1"
            ),
            Button("Применить", type="submit", cls="btn btn-primary btn-sm"),
            A("×", href=f"/dashboard?per_page={per_page}", cls="btn btn-ghost btn-sm text-xl", title="Сбросить"),
            cls="flex gap-2 mb-4"
        ),

        # Фильтры в три колонки
        Div(
            # Левая колонка - Статусы dropdown + Создатели
            Div(
                # Статусы
                Div(
                    Details(
                        Summary(
                            Span(
                                f"{len(current_statuses)} Selected" if current_statuses else "Статусы",
                                id="status-summary-text"
                            ),
                            Span("▲", cls="ml-auto text-primary", style="font-size: 0.75rem;"),
                            cls="btn btn-sm btn-outline w-full justify-between",
                            style="text-align: left;"
                        ),
                        Ul(
                            Li(
                                Label(
                                    Input(
                                        type="checkbox",
                                        name="status",
                                        value="pending",
                                        checked=("pending" in current_statuses),
                                        cls="checkbox checkbox-sm checkbox-primary",
                                        onchange="updateStatusCount()"
                                    ),
                                    Span("⏳ Ожидает", cls="ml-2"),
                                    cls="label cursor-pointer justify-start gap-2 p-2"
                                )
                            ),
                            Li(
                                Label(
                                    Input(
                                        type="checkbox",
                                        name="status",
                                        value="scheduled",
                                        checked=("scheduled" in current_statuses),
                                        cls="checkbox checkbox-sm checkbox-primary",
                                        onchange="updateStatusCount()"
                                    ),
                                    Span("📅 Запланировано", cls="ml-2"),
                                    cls="label cursor-pointer justify-start gap-2 p-2"
                                )
                            ),
                            Li(
                                Label(
                                    Input(
                                        type="checkbox",
                                        name="status",
                                        value="paid",
                                        checked=("paid" in current_statuses),
                                        cls="checkbox checkbox-sm checkbox-primary",
                                        onchange="updateStatusCount()"
                                    ),
                                    Span("✅ Оплачено", cls="ml-2"),
                                    cls="label cursor-pointer justify-start gap-2 p-2"
                                )
                            ),
                            Li(
                                Label(
                                    Input(
                                        type="checkbox",
                                        name="status",
                                        value="cancelled",
                                        checked=("cancelled" in current_statuses),
                                        cls="checkbox checkbox-sm checkbox-primary",
                                        onchange="updateStatusCount()"
                                    ),
                                    Span("❌ Отменено", cls="ml-2"),
                                    cls="label cursor-pointer justify-start gap-2 p-2"
                                )
                            ),
                            cls="menu dropdown-content bg-base-100 rounded-box z-[1] w-full p-2 shadow mt-1"
                        ),
                        cls="dropdown w-full"
                    ),
                    cls="form-control mb-3" if show_creator_filter else "form-control"
                ),

                # Фильтр по создателю (только для Owner/Manager)
                Div(
                    Select(
                        Option("👤 Все создатели", value="", selected=(not creator_id)),
                        *[
                            Option(
                                user.display_name,
                                value=str(user.id),
                                selected=(creator_id == user.id)
                            )
                            for user in (users or [])
                        ],
                        name="creator_id",
                        cls="select select-sm select-bordered w-full"
                    ),
                    cls="form-control"
                ) if show_creator_filter else None,

                cls="form-control"
            ),

            # Центральная колонка - Период (два календаря)
            Div(
                Div(
                    Input(
                        type="text",
                        name="date_from",
                        id="date_from_picker",
                        value=date_from,
                        placeholder="📅 Дата от",
                        cls="input input-sm input-bordered w-full"
                    ),
                    cls="form-control mb-2"
                ),
                Div(
                    Input(
                        type="text",
                        name="date_to",
                        id="date_to_picker",
                        value=date_to,
                        placeholder="📅 Дата до",
                        cls="input input-sm input-bordered w-full"
                    ),
                    cls="form-control"
                ),
                cls="form-control"
            ),

            # Правая колонка - Диапазон сумм
            Div(
                Input(
                    type="number",
                    name="amount_min",
                    value=amount_min,
                    placeholder="💰 Сумма от",
                    cls="input input-sm input-bordered w-full mb-2"
                ),
                Input(
                    type="number",
                    name="amount_max",
                    value=amount_max,
                    placeholder="💰 Сумма до",
                    cls="input input-sm input-bordered w-full"
                ),
                cls="form-control"
            ),

            cls="grid grid-cols-1 md:grid-cols-3 gap-4"
        ),

        # Скрытое поле для сохранения per_page
        Input(type="hidden", name="per_page", value=str(per_page)),

        method="GET",
        action="/dashboard"
    )


def generate_page_numbers(current_page: int, total_pages: int) -> List[tuple]:
    """Генерирует номера страниц с эллипсисами

    Returns:
        List of tuples: [(page_number, is_ellipsis), ...]
        Например: [(1, False), (2, False), (None, True), (45, False), (46, False)]
    """
    if total_pages <= 7:
        # Показываем все страницы
        return [(i, False) for i in range(1, total_pages + 1)]

    pages = []

    # Всегда показываем первую страницу
    pages.append((1, False))

    # Определяем диапазон вокруг текущей страницы
    if current_page <= 4:
        # Начало: 1 2 3 4 5 ... last
        for i in range(2, min(6, total_pages)):
            pages.append((i, False))
        if total_pages > 6:
            pages.append((None, True))  # эллипсис
        pages.append((total_pages, False))
    elif current_page >= total_pages - 3:
        # Конец: 1 ... 45 46 47 48 49
        pages.append((None, True))
        for i in range(total_pages - 4, total_pages):
            pages.append((i, False))
        pages.append((total_pages, False))
    else:
        # Середина: 1 ... 23 24 25 ... 50
        pages.append((None, True))
        for i in range(current_page - 1, current_page + 2):
            pages.append((i, False))
        pages.append((None, True))
        pages.append((total_pages, False))

    return pages


def pagination_controls(
    current_page: int,
    total_pages: int,
    per_page: int,
    filter_status: str,
    base_path: str = "/dashboard"
) -> Div:
    """Элементы управления пагинацией с эллипсисами"""

    if total_pages <= 1:
        return Div()  # Не показываем пагинацию если одна страница

    page_numbers = generate_page_numbers(current_page, total_pages)

    # Кнопки страниц
    buttons = []

    # Кнопка "Предыдущая"
    prev_disabled = current_page <= 1
    buttons.append(
        A(
            "«",
            href=f"{base_path}?filter={filter_status}&page={current_page - 1}&per_page={per_page}",
            cls=f"join-item btn {'btn-disabled' if prev_disabled else ''}"
        ) if not prev_disabled else
        Button("«", cls="join-item btn btn-disabled", disabled=True)
    )

    # Номера страниц
    for page_num, is_ellipsis in page_numbers:
        if is_ellipsis:
            buttons.append(
                Button("...", cls="join-item btn btn-disabled", disabled=True)
            )
        else:
            is_active = page_num == current_page
            buttons.append(
                A(
                    str(page_num),
                    href=f"{base_path}?filter={filter_status}&page={page_num}&per_page={per_page}",
                    cls=f"join-item btn {'btn-active' if is_active else ''}"
                )
            )

    # Кнопка "Следующая"
    next_disabled = current_page >= total_pages
    buttons.append(
        A(
            "»",
            href=f"{base_path}?filter={filter_status}&page={current_page + 1}&per_page={per_page}",
            cls=f"join-item btn {'btn-disabled' if next_disabled else ''}"
        ) if not next_disabled else
        Button("»", cls="join-item btn btn-disabled", disabled=True)
    )

    return Div(*buttons, cls="join")


def per_page_selector(
    current_per_page: int,
    current_page: int,
    filter_status: str,
    base_path: str = "/dashboard"
) -> Select:
    """Выпадающий список для выбора количества записей на странице"""

    options = [10, 25, 50, 100]

    return Select(
        *[
            Option(
                f"{value} записей",
                value=str(value),
                selected=(value == current_per_page)
            )
            for value in options
        ],
        cls="select select-bordered select-sm",
        onchange=f"window.location.href='{base_path}?filter={filter_status}&page=1&per_page=' + this.value"
    )


def pagination_footer(
    current_page: int,
    total_pages: int,
    per_page: int,
    total_items: int,
    filter_status: str
) -> Div:
    """Футер с пагинацией и выбором количества записей"""

    # Подсчет диапазона показанных записей
    start_item = (current_page - 1) * per_page + 1
    end_item = min(current_page * per_page, total_items)

    return Div(
        # Информация о записях
        Div(
            Span(
                f"Показано {start_item}-{end_item} из {total_items} записей",
                cls="text-sm text-gray-600"
            ),
            cls="flex items-center"
        ),

        # Пагинация (слева)
        Div(
            pagination_controls(current_page, total_pages, per_page, filter_status),
            cls="flex items-center"
        ),

        # Выбор количества (справа)
        Div(
            Label("На странице:", cls="text-sm mr-2"),
            per_page_selector(per_page, current_page, filter_status),
            cls="flex items-center gap-2"
        ),

        cls="flex justify-between items-center mt-4 p-4"
    )


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

        # Плательщик
        Div(
            Label(
                Span("Плательщик", cls="label-text"),
                Input(
                    type_="checkbox",
                    name="is_billing_contact",
                    value="true",
                    checked=user.is_billing_contact,
                    cls="toggle toggle-primary"
                ),
                cls="label cursor-pointer justify-between"
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

        # Плательщик
        Div(
            Label(
                Span("Плательщик", cls="label-text"),
                Input(
                    type_="checkbox",
                    name="is_billing_contact",
                    value="true",
                    cls="toggle toggle-primary"
                ),
                cls="label cursor-pointer justify-between"
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
