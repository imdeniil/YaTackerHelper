"""Base templates and layouts."""

from fasthtml.common import *


def Layout(title: str, *content, user=None):
    """Base layout template with drawer navigation.

    Args:
        title: Page title
        *content: Page content components
        user: Current logged-in user (optional)
    """
    if user:
        # Layout with drawer for authenticated users
        return Html(
            Head(
                Meta(charset="utf-8"),
                Meta(name="viewport", content="width=device-width, initial-scale=1"),
                Title(f"{title} - ZoukLike"),
                Script(src="https://cdn.tailwindcss.com"),
                Link(href="https://cdn.jsdelivr.net/npm/daisyui@4.12.14/dist/full.min.css", rel="stylesheet", type_="text/css"),
                Script(src="https://unpkg.com/htmx.org@1.9.10"),
            ),
            Body(
                Div(
                    # Drawer toggle (checkbox)
                    Input(type="checkbox", id="main-drawer", cls="drawer-toggle"),
                    # Page content
                    Div(
                        Header(user=user),
                        Main(*content, cls="container mx-auto px-4 py-8"),
                        Footer(),
                        cls="drawer-content flex flex-col min-h-screen",
                    ),
                    # Drawer sidebar
                    Div(
                        Label(htmlFor="main-drawer", cls="drawer-overlay"),
                        Div(
                            DrawerMenu(user=user),
                            cls="menu p-4 w-80 min-h-full bg-base-200 text-base-content",
                        ),
                        cls="drawer-side",
                    ),
                    cls="drawer",
                ),
            ),
            data_theme="light",
        )
    else:
        # Simple layout for non-authenticated users
        return Html(
            Head(
                Meta(charset="utf-8"),
                Meta(name="viewport", content="width=device-width, initial-scale=1"),
                Title(f"{title} - ZoukLike"),
                Script(src="https://cdn.tailwindcss.com"),
                Link(href="https://cdn.jsdelivr.net/npm/daisyui@4.12.14/dist/full.min.css", rel="stylesheet", type_="text/css"),
                Script(src="https://unpkg.com/htmx.org@1.9.10"),
            ),
            Body(
                Header(user=user),
                Main(*content, cls="container mx-auto px-4 py-8"),
                Footer(),
                cls="min-h-screen flex flex-col",
            ),
            data_theme="light",
        )


def Header(user=None):
    """Header component with dropdown menu.

    Args:
        user: Current logged-in user (optional)
    """
    if user:
        # Logged in navigation with drawer toggle and dropdown
        return Div(
            Div(
                Div(
                    # Drawer toggle button
                    Label(
                        htmlFor="main-drawer",
                        cls="btn btn-ghost btn-circle drawer-button",
                        children=[
                            Svg(
                                xmlns="http://www.w3.org/2000/svg",
                                cls="h-5 w-5",
                                fill="none",
                                viewBox="0 0 24 24",
                                stroke="currentColor",
                                children=[
                                    Path(
                                        strokeLinecap="round",
                                        strokeLinejoin="round",
                                        strokeWidth="2",
                                        d="M4 6h16M4 12h16M4 18h7",
                                    )
                                ],
                            )
                        ],
                    ),
                    cls="flex-none",
                ),
                # Logo/Brand
                Div(
                    A("ZoukLike", href="/", cls="btn btn-ghost text-xl"),
                    cls="flex-1",
                ),
                # User dropdown menu
                Div(
                    Div(
                        Div(tabindex="0", role="button", cls="btn btn-ghost btn-circle avatar",
                            children=[
                                Div(
                                    Span(user.get("email", "U")[0].upper(), cls="text-xl"),
                                    cls="w-10 rounded-full bg-primary text-primary-content flex items-center justify-center",
                                )
                            ]
                        ),
                        Ul(
                            Li(
                                A("Главная", href="/dashboard")
                            ),
                            Li(
                                A("Настройки", href="/settings")
                            ),
                            Li(
                                A("Выйти", href="/auth/logout")
                            ),
                            tabindex="0",
                            cls="menu menu-sm dropdown-content mt-3 z-[1] p-2 shadow bg-base-100 rounded-box w-52",
                        ),
                        cls="dropdown dropdown-end",
                    ),
                    cls="flex-none",
                ),
                cls="navbar bg-base-100 shadow-lg",
            ),
            cls="mb-8",
        )
    else:
        # Not logged in navigation
        return Div(
            Div(
                # Logo/Brand
                A("ZoukLike", href="/", cls="btn btn-ghost text-xl"),
                # Navigation
                Div(
                    A("Войти", href="/auth/login", cls="btn btn-ghost"),
                    A("Регистрация", href="/auth/register", cls="btn btn-primary"),
                    cls="flex gap-2",
                ),
                cls="navbar bg-base-100 shadow-lg",
            ),
            cls="mb-8",
        )


def DrawerMenu(user=None):
    """Drawer sidebar menu.

    Args:
        user: Current logged-in user (optional)
    """
    return Ul(
        Li(
            Div(
                Span(user.get("email", "User")[0].upper(), cls="text-2xl"),
                cls="w-12 h-12 rounded-full bg-primary text-primary-content flex items-center justify-center mb-2",
            ),
            Div(
                Strong(user.get("email", "User")),
                cls="text-sm",
            ),
            cls="mb-4 text-center",
        ),
        Div(cls="divider"),
        Li(A(
            Svg(xmlns="http://www.w3.org/2000/svg", cls="h-5 w-5", fill="none", viewBox="0 0 24 24", stroke="currentColor",
                children=[Path(strokeLinecap="round", strokeLinejoin="round", strokeWidth="2", d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6")]),
            Span("Главная"),
            href="/dashboard",
        )),
        Li(A(
            Svg(xmlns="http://www.w3.org/2000/svg", cls="h-5 w-5", fill="none", viewBox="0 0 24 24", stroke="currentColor",
                children=[Path(strokeLinecap="round", strokeLinejoin="round", strokeWidth="2", d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z")]),
            Span("Профиль"),
            href="/profile",
        )),
        Li(A(
            Svg(xmlns="http://www.w3.org/2000/svg", cls="h-5 w-5", fill="none", viewBox="0 0 24 24", stroke="currentColor",
                children=[Path(strokeLinecap="round", strokeLinejoin="round", strokeWidth="2", d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z M15 12a3 3 0 11-6 0 3 3 0 016 0z")]),
            Span("Настройки"),
            href="/settings",
        )),
        Div(cls="divider"),
        Li(A(
            Svg(xmlns="http://www.w3.org/2000/svg", cls="h-5 w-5", fill="none", viewBox="0 0 24 24", stroke="currentColor",
                children=[Path(strokeLinecap="round", strokeLinejoin="round", strokeWidth="2", d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1")]),
            Span("Выйти"),
            href="/auth/logout",
            cls="text-error",
        )),
        cls="menu",
    )


def Footer():
    """Footer component."""
    return Div(
        Div(
            P(
                "ZoukLike - Образовательная платформа",
                cls="text-center text-sm text-gray-600",
            ),
            cls="footer footer-center p-4 bg-base-200 text-base-content mt-auto",
        ),
    )


def Card(title: str, *content):
    """Card component.

    Args:
        title: Card title
        *content: Card content
    """
    return Div(
        Div(
            H2(title, cls="card-title"),
            *content,
            cls="card-body",
        ),
        cls="card bg-base-100 shadow-xl",
    )


def Alert(message: str, type: str = "info"):
    """Alert component.

    Args:
        message: Alert message
        type: Alert type (info, success, warning, error)
    """
    alert_classes = {
        "info": "alert-info",
        "success": "alert-success",
        "warning": "alert-warning",
        "error": "alert-error",
    }

    return Div(
        Span(message),
        cls=f"alert {alert_classes.get(type, 'alert-info')} mb-4",
    )


def Modal(id: str, title: str, *content, actions=None):
    """Modal dialog component.

    Args:
        id: Modal ID for toggling
        title: Modal title
        *content: Modal content
        actions: Modal action buttons (optional)
    """
    return Div(
        Input(type="checkbox", id=id, cls="modal-toggle"),
        Div(
            Div(
                H3(title, cls="font-bold text-lg mb-4"),
                Div(*content, cls="py-4"),
                Div(
                    *actions if actions else [
                        Label("Закрыть", htmlFor=id, cls="btn")
                    ],
                    cls="modal-action",
                ),
                cls="modal-box",
            ),
            Label(cls="modal-backdrop", htmlFor=id),
            cls="modal",
        ),
    )


def ConfirmModal(id: str, title: str, message: str, confirm_href: str, confirm_text: str = "Подтвердить"):
    """Confirmation modal component.

    Args:
        id: Modal ID
        title: Modal title
        message: Confirmation message
        confirm_href: URL for confirmation action
        confirm_text: Confirmation button text
    """
    return Modal(
        id,
        title,
        P(message, cls="text-base"),
        actions=[
            Label("Отмена", htmlFor=id, cls="btn btn-ghost"),
            A(confirm_text, href=confirm_href, cls="btn btn-primary"),
        ],
    )


def AuthLayout(title: str, hero_title: str, hero_description: str, form_content):
    """Layout for authentication pages with Hero component.

    Args:
        title: Page title
        hero_title: Hero section title
        hero_description: Hero section description
        form_content: Form element to display
    """
    return Html(
        Head(
            Meta(charset="utf-8"),
            Meta(name="viewport", content="width=device-width, initial-scale=1"),
            Title(f"{title} - ZoukLike"),
            Script(src="https://cdn.tailwindcss.com"),
            Link(href="https://cdn.jsdelivr.net/npm/daisyui@4.12.14/dist/full.min.css", rel="stylesheet", type_="text/css"),
            Script(src="https://unpkg.com/htmx.org@1.9.10"),
        ),
        Body(
            Div(
                Div(
                    Div(
                        # Hero text section
                        Div(
                            H1(hero_title, cls="text-5xl font-bold"),
                            P(hero_description, cls="py-6"),
                            cls="text-center lg:text-left",
                        ),
                        # Card with form
                        Div(
                            Div(
                                form_content,
                                cls="card-body",
                            ),
                            cls="card bg-base-100 w-full max-w-sm shrink-0 shadow-2xl",
                        ),
                        cls="hero-content flex-col lg:flex-row-reverse",
                    ),
                    cls="hero bg-base-200 min-h-screen",
                ),
            ),
        ),
        data_theme="light",
    )


def AuthLayoutWithRole(title: str, hero_title: str, hero_description: str, form_content, role_description_id: str = "role-description"):
    """Layout for authentication pages with Hero component and role description.

    Args:
        title: Page title
        hero_title: Hero section title
        hero_description: Hero section description
        form_content: Form element to display
        role_description_id: ID for the role description div (for HTMX updates)
    """
    return Html(
        Head(
            Meta(charset="utf-8"),
            Meta(name="viewport", content="width=device-width, initial-scale=1"),
            Title(f"{title} - ZoukLike"),
            Script(src="https://cdn.tailwindcss.com"),
            Link(href="https://cdn.jsdelivr.net/npm/daisyui@4.12.14/dist/full.min.css", rel="stylesheet", type_="text/css"),
            Script(src="https://unpkg.com/htmx.org@1.9.10"),
        ),
        Body(
            Div(
                # Hero section with title
                Div(
                    H1(hero_title, cls="text-4xl font-bold text-center mb-2"),
                    P(hero_description, cls="text-center text-gray-600 mb-8"),
                    cls="container mx-auto px-4 pt-8",
                ),
                # Two column layout: form + role description
                Div(
                    Div(
                        # Left: Form card
                        Div(
                            Div(
                                form_content,
                                cls="card-body",
                            ),
                            cls="card bg-base-100 shadow-2xl h-full",
                        ),
                        cls="w-full lg:w-1/2 px-4",
                    ),
                    # Right: Role description
                    Div(
                        Div(
                            Div(
                                # Default content for student role
                                Div(
                                    Span("🎓", cls="text-6xl"),
                                    cls="flex justify-center mb-4",
                                ),
                                H3("Ученик", cls="text-2xl font-bold text-center mb-4"),
                                P("Покупайте абонементы, записывайтесь на занятия и отслеживайте свой прогресс.", cls="text-left text-gray-600"),
                                Div(
                                    H4("Возможности:", cls="font-semibold text-base mb-3"),
                                    Ul(
                                        Li("Просмотр и покупка абонементов", cls="text-sm"),
                                        Li("Запись на занятия", cls="text-sm"),
                                        Li("Отслеживание посещений", cls="text-sm"),
                                        Li("История покупок", cls="text-sm"),
                                        Li("Управление заморозками", cls="text-sm"),
                                        cls="list-disc list-inside text-gray-700 space-y-2 pl-4",
                                    ),
                                    cls="mt-6 mb-12",
                                ),
                                cls="card-body",
                                id=role_description_id,
                            ),
                            cls="card bg-base-100 shadow-xl h-full",
                        ),
                        cls="w-full lg:w-1/2 px-4 mt-8 lg:mt-0",
                    ),
                    cls="container mx-auto flex flex-col lg:flex-row items-stretch justify-center pb-8",
                ),
                cls="bg-base-200 min-h-screen",
            ),
        ),
        data_theme="light",
    )
