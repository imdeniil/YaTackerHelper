"""Layout компоненты - navbar, page_layout"""

from typing import Any
from fasthtml.common import *


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
        cls="mb-0"
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
                cls="container mx-auto px-4 py-4"
            ),
            # Подключение внешнего JavaScript файла
            Script(src="/static/js/dashboard.js"),
            data_theme="light"
        )
    )
