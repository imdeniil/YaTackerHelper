"""Filter компоненты"""

from typing import List
from fasthtml.common import *


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
    date_type: str = "created",
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
                cls="input input-sm input-bordered flex-1",
                id="search-input"
            ),
            Button("↵", type="submit", cls="btn btn-ghost btn-sm", title="Применить", id="apply-filters-btn"),
            A("⟲", href=f"/dashboard?per_page={per_page}", cls="btn btn-ghost btn-sm", title="Сбросить", id="reset-filters-btn"),
            Button("📊", type="button", cls="btn btn-ghost btn-sm", title="Аналитика", id="analytics-btn", onclick="openAnalyticsModal()"),
            Button("📥", type="button", cls="btn btn-ghost btn-sm", title="Экспорт в Excel", id="export-btn", onclick="exportToExcel()"),
            Button("+", type="button", cls="btn btn-ghost btn-sm", title="Создать запрос", id="create-request-btn", onclick="openCreateModal()"),
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
                            Span("▼", cls="ml-auto", id="status-arrow", style="font-size: 0.75rem;"),
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
                        cls="dropdown w-full",
                        id="status-dropdown"
                    ),
                    cls="form-control mb-3" if show_creator_filter else "form-control"
                ),

                # Фильтр по создателю (только для Owner/Manager)
                Div(
                    Details(
                        Summary(
                            Span(
                                "👤 " + (next((u.display_name for u in (users or []) if u.id == creator_id), "Все создатели")),
                                id="creator-summary-text"
                            ),
                            Span("▼", cls="ml-auto", id="creator-arrow", style="font-size: 0.75rem;"),
                            cls="btn btn-sm btn-outline w-full justify-between",
                            style="text-align: left;",
                            onclick="toggleCreatorArrow()"
                        ),
                        Ul(
                            Li(
                                Label(
                                    Input(
                                        type="radio",
                                        name="creator_id",
                                        value="",
                                        checked=(not creator_id),
                                        cls="radio radio-sm radio-primary",
                                        onchange="updateCreatorText(this)"
                                    ),
                                    Span("👤 Все создатели", cls="ml-2"),
                                    cls="label cursor-pointer justify-start gap-2 p-2"
                                )
                            ),
                            *[
                                Li(
                                    Label(
                                        Input(
                                            type="radio",
                                            name="creator_id",
                                            value=str(user.id),
                                            checked=(creator_id == user.id),
                                            cls="radio radio-sm radio-primary",
                                            onchange="updateCreatorText(this)"
                                        ),
                                        Span(user.display_name, cls="ml-2"),
                                        cls="label cursor-pointer justify-start gap-2 p-2"
                                    )
                                )
                                for user in (users or [])
                            ],
                            cls="menu dropdown-content bg-base-100 rounded-box z-[1] w-full p-2 shadow mt-1"
                        ),
                        cls="dropdown w-full",
                        id="creator-dropdown"
                    ),
                    cls="form-control"
                ) if show_creator_filter else None,

                cls="form-control"
            ),

            # Центральная колонка - Период (два календаря с табами)
            Div(
                # Табы для выбора типа даты
                Div(
                    Button(
                        "Дата создания",
                        type="button",
                        cls=f"btn btn-xs flex-1 {'btn-primary' if date_type == 'created' else 'btn-ghost'} date-type-tab",
                        data_date_type="created",
                        id="tab-created",
                        onclick="switchDateType('created')"
                    ),
                    Button(
                        "Дата оплаты",
                        type="button",
                        cls=f"btn btn-xs flex-1 {'btn-primary' if date_type == 'paid' else 'btn-ghost'} date-type-tab",
                        data_date_type="paid",
                        id="tab-paid",
                        onclick="switchDateType('paid')"
                    ),
                    cls="flex w-full mb-2"
                ),
                # Отступ для выравнивания с "Сумма до"
                Div(cls="mb-2"),
                # Поля дат в одну строку
                Div(
                    Input(
                        type="text",
                        name="date_from",
                        id="date_from_picker",
                        value=date_from,
                        placeholder="📅 От",
                        cls="input input-sm input-bordered flex-1"
                    ),
                    Input(
                        type="text",
                        name="date_to",
                        id="date_to_picker",
                        value=date_to,
                        placeholder="📅 До",
                        cls="input input-sm input-bordered flex-1"
                    ),
                    cls="flex gap-2"
                ),
                # Скрытое поле для типа даты
                Input(type="hidden", name="date_type", value=date_type, id="date-type-input"),
                cls="form-control"
            ),

            # Правая колонка - Диапазон сумм
            Div(
                Input(
                    type="number",
                    name="amount_min",
                    value=amount_min,
                    placeholder="💰 Сумма от",
                    cls="input input-sm input-bordered w-full mb-2",
                    id="amount-min"
                ),
                Input(
                    type="number",
                    name="amount_max",
                    value=amount_max,
                    placeholder="💰 Сумма до",
                    cls="input input-sm input-bordered w-full",
                    id="amount-max"
                ),
                cls="form-control"
            ),

            cls="grid grid-cols-1 md:grid-cols-3 gap-4"
        ),

        # Скрытое поле для сохранения per_page
        Input(type="hidden", name="per_page", value=str(per_page), id="per-page-input"),

        method="GET",
        action="/dashboard",
        id="filters-form"
    )
