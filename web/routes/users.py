"""Маршруты для управления пользователями"""

import logging
from fasthtml.common import *
from web.database import get_session, UserCRUD
from web.config import WebConfig
from web.components import (
    page_layout, user_table, card, user_edit_form, user_create_form
)
from web.telegram_utils import get_user_profile_photo_url, get_fallback_avatar_url
from bot.database.models import UserRole
from .decorators import require_auth, require_role

logger = logging.getLogger(__name__)


def setup_user_routes(app, config: WebConfig):
    """Настраивает маршруты для управления пользователями"""

    @app.get("/users")
    @require_auth
    @require_role(UserRole.OWNER.value)
    async def users_list(sess):
        """Список всех пользователей (только для Owner)"""
        user_id = sess.get('user_id')
        display_name = sess.get('display_name')
        role = sess.get('role')

        async with get_session() as session:
            current_user = await UserCRUD.get_user_by_id(session, user_id)
            users = await UserCRUD.get_all_users(session)

        content = Div(
            Div(
                H1("Управление пользователями", cls="text-3xl font-bold"),
                A("+ Создать пользователя", href="/users/create", cls="btn btn-primary"),
                cls="flex justify-between items-center mb-6"
            ),

            Div(
                Div(
                    user_table(users),
                    cls="card-body p-0"
                ),
                cls="card bg-base-100 shadow-xl"
            )
        )

        # Получаем аватар из Telegram
        avatar_url = await get_user_profile_photo_url(config.bot_token, current_user.telegram_id) if current_user else None
        if not avatar_url:
            avatar_url = get_fallback_avatar_url(display_name)

        return page_layout("Управление пользователями", content, display_name, role, avatar_url)

    @app.get("/users/{user_id}/edit")
    @require_auth
    @require_role(UserRole.OWNER.value)
    async def user_edit_page(sess, user_id: int):
        """Страница редактирования пользователя (только для Owner)"""
        current_user_id = sess.get('user_id')
        display_name = sess.get('display_name')
        role = sess.get('role')

        async with get_session() as session:
            current_user = await UserCRUD.get_user_by_id(session, current_user_id)
            user_to_edit = await UserCRUD.get_user_by_id(session, user_id)

            if not user_to_edit:
                return RedirectResponse('/users', status_code=303)

        content = Div(
            A("← Назад к списку пользователей", href="/users", cls="btn btn-ghost btn-sm mb-4"),
            card(f"Редактирование пользователя: {user_to_edit.display_name}", user_edit_form(user_to_edit))
        )

        # Получаем аватар из Telegram
        avatar_url = await get_user_profile_photo_url(config.bot_token, current_user.telegram_id) if current_user else None
        if not avatar_url:
            avatar_url = get_fallback_avatar_url(display_name)

        return page_layout(
            "Редактирование пользователя",
            content,
            display_name,
            role,
            avatar_url
        )

    @app.post("/users/{user_id}/edit")
    @require_auth
    @require_role(UserRole.OWNER.value)
    async def user_edit_submit(
        sess,
        user_id: int,
        display_name: str,
        telegram_username: str,
        tracker_login: str,
        role: str,
        is_billing_contact: str = None
    ):
        """Сохранение изменений пользователя"""
        current_user_id = sess.get('user_id')

        async with get_session() as session:
            # Обновляем данные пользователя
            await UserCRUD.update_user(
                session=session,
                user_id=user_id,
                display_name=display_name,
                telegram_username=telegram_username.lstrip("@"),
                tracker_login=tracker_login if tracker_login else None,
                role=UserRole(role),
                is_billing_contact=(is_billing_contact == "true")
            )

            logger.info(f"Owner {current_user_id} обновил данные пользователя #{user_id}")

        return RedirectResponse('/users', status_code=303)

    @app.get("/users/create")
    @require_auth
    @require_role(UserRole.OWNER.value)
    async def user_create_page(sess):
        """Страница создания нового пользователя (только для Owner)"""
        current_user_id = sess.get('user_id')
        display_name = sess.get('display_name')
        role = sess.get('role')

        async with get_session() as session:
            current_user = await UserCRUD.get_user_by_id(session, current_user_id)

        content = Div(
            A("← Назад к списку пользователей", href="/users", cls="btn btn-ghost btn-sm mb-4"),
            card("Создание нового пользователя", user_create_form())
        )

        # Получаем аватар из Telegram
        avatar_url = await get_user_profile_photo_url(config.bot_token, current_user.telegram_id) if current_user else None
        if not avatar_url:
            avatar_url = get_fallback_avatar_url(display_name)

        return page_layout(
            "Создание пользователя",
            content,
            display_name,
            role,
            avatar_url
        )

    @app.post("/users/create")
    @require_auth
    @require_role(UserRole.OWNER.value)
    async def user_create_submit(
        sess,
        display_name: str,
        telegram_username: str,
        tracker_login: str,
        role: str,
        is_billing_contact: str = None
    ):
        """Создание нового пользователя"""
        current_user_id = sess.get('user_id')

        async with get_session() as session:
            # Создаем нового пользователя
            new_user = await UserCRUD.create_user(
                session=session,
                telegram_username=telegram_username.lstrip("@"),
                display_name=display_name,
                role=UserRole(role),
                tracker_login=tracker_login if tracker_login else None,
                is_billing_contact=(is_billing_contact == "true")
            )

            logger.info(f"Owner {current_user_id} создал нового пользователя #{new_user.id}")

        return RedirectResponse('/users', status_code=303)
