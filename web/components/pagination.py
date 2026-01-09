"""Pagination компоненты"""

from typing import List
from fasthtml.common import *


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
            href="#",
            cls=f"join-item btn {'btn-disabled' if prev_disabled else ''} pagination-link",
            data_page=str(current_page - 1)
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
                    href="#",
                    cls=f"join-item btn {'btn-active' if is_active else ''} pagination-link",
                    data_page=str(page_num)
                )
            )

    # Кнопка "Следующая"
    next_disabled = current_page >= total_pages
    buttons.append(
        A(
            "»",
            href="#",
            cls=f"join-item btn {'btn-disabled' if next_disabled else ''} pagination-link",
            data_page=str(current_page + 1)
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

    options = [10, 20, 25, 50, 100]

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
        id="per-page-selector",
        onchange="handlePerPageChange(this.value)"
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
