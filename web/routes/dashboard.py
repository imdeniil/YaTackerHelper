"""Маршруты dashboard для разных ролей"""

import logging
from fasthtml.common import *
from web.database import get_session, UserCRUD, PaymentRequestCRUD
from web.config import WebConfig
from bot.database.models import UserRole

logger = logging.getLogger(__name__)


def require_auth(f):
    """Декоратор для проверки авторизации"""
    async def wrapper(sess, *args, **kwargs):
        user_id = sess.get('user_id')
        if not user_id:
            return RedirectResponse('/login', status_code=303)
        return await f(sess, *args, **kwargs)
    return wrapper


def setup_dashboard_routes(app, config: WebConfig):
    """Настраивает маршруты dashboard

    Args:
        app: FastHTML приложение
        config: Конфигурация веб-приложения
    """

    @app.get("/dashboard")
    @require_auth
    async def dashboard(sess):
        """Главная страница dashboard - роутинг по ролям"""
        user_id = sess.get('user_id')
        role = sess.get('role')
        is_billing_contact = sess.get('is_billing_contact')
        display_name = sess.get('display_name')

        # Получаем пользователя из БД для актуальных данных
        async with get_session() as session:
            user = await UserCRUD.get_user_by_id(session, user_id)

            if not user:
                sess.clear()
                return RedirectResponse('/login', status_code=303)

        return Html(
            Head(
                Title("Dashboard - YaTackerHelper"),
                Meta(charset="utf-8"),
                Meta(name="viewport", content="width=device-width, initial-scale=1"),
            ),
            Body(
                # Navbar
                Div(
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
                ),

                # Main content
                Div(
                    H1(f"Добро пожаловать, {display_name}!", cls="text-3xl font-bold mb-6"),

                    Div(
                        Div(
                            Div(
                                H2("🎭 Ваша роль", cls="card-title"),
                                P(f"Роль: {role.upper()}", cls="text-lg"),
                                P(f"Billing Contact: {'Да' if is_billing_contact else 'Нет'}",
                                  cls="text-sm text-gray-600"),
                                cls="card-body"
                            ),
                            cls="card bg-base-100 shadow-xl"
                        ),

                        Div(
                            Div(
                                H2("🚧 В разработке", cls="card-title"),
                                P("Dashboard находится в процессе разработки.", cls="text-gray-600"),
                                P("Скоро здесь появится функционал для вашей роли.", cls="text-sm text-gray-500 mt-2"),
                                cls="card-body"
                            ),
                            cls="card bg-base-100 shadow-xl"
                        ),

                        cls="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6"
                    ),

                    cls="container mx-auto p-6"
                ),

                data_theme="light"
            )
        )
