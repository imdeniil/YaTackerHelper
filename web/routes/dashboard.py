"""Маршруты dashboard для разных ролей"""

import logging
from functools import wraps
from fasthtml.common import *
from web.database import get_session, UserCRUD, PaymentRequestCRUD
from web.config import WebConfig
from web.components import (
    page_layout, stat_item, payment_request_table,
    create_payment_form, filter_tabs, user_table, card,
    payment_request_detail, user_edit_form, user_create_form
)
from web.telegram_utils import get_user_profile_photo_url, get_fallback_avatar_url
from bot.database.models import UserRole, PaymentRequestStatus

logger = logging.getLogger(__name__)


def require_auth(f):
    """Декоратор для проверки авторизации"""
    @wraps(f)
    async def wrapper(sess, *args, **kwargs):
        user_id = sess.get('user_id')
        if not user_id:
            return RedirectResponse('/login', status_code=303)
        return await f(sess, *args, **kwargs)
    return wrapper


def require_role(*allowed_roles):
    """Декоратор для проверки роли"""
    def decorator(f):
        @wraps(f)
        async def wrapper(sess, *args, **kwargs):
            role = sess.get('role')
            if role not in allowed_roles:
                return RedirectResponse('/dashboard', status_code=303)
            return await f(sess, *args, **kwargs)
        return wrapper
    return decorator


def setup_dashboard_routes(app, config: WebConfig):
    """Настраивает маршруты dashboard

    Args:
        app: FastHTML приложение
        config: Конфигурация веб-приложения
    """

    @app.get("/dashboard")
    @require_auth
    async def dashboard(sess, filter: str = "all"):
        """Главная страница dashboard - роутинг по ролям"""
        user_id = sess.get('user_id')
        role = sess.get('role')
        display_name = sess.get('display_name')

        # Получаем пользователя из БД для актуальных данных
        async with get_session() as session:
            user = await UserCRUD.get_user_by_id(session, user_id)

            if not user:
                sess.clear()
                return RedirectResponse('/login', status_code=303)

            # Роутинг по ролям
            if role == UserRole.WORKER.value:
                return await worker_dashboard(session, user, filter, config.bot_token)
            elif role in [UserRole.OWNER.value, UserRole.MANAGER.value]:
                return await owner_dashboard(session, user, role, filter, config.bot_token)

        # Fallback
        return RedirectResponse('/login', status_code=303)

    async def worker_dashboard(session, user, filter_status, bot_token):
        """Dashboard для Worker - создание и просмотр своих запросов"""
        # Получаем все запросы пользователя
        all_requests = await PaymentRequestCRUD.get_user_payment_requests(session, user.id)

        # Фильтруем по статусу
        if filter_status == "pending":
            requests = [r for r in all_requests if r.status == PaymentRequestStatus.PENDING.value]
        elif filter_status == "scheduled":
            requests = [r for r in all_requests if r.status in [
                PaymentRequestStatus.SCHEDULED_TODAY.value,
                PaymentRequestStatus.SCHEDULED_DATE.value
            ]]
        elif filter_status == "paid":
            requests = [r for r in all_requests if r.status == PaymentRequestStatus.PAID.value]
        elif filter_status == "cancelled":
            requests = [r for r in all_requests if r.status == PaymentRequestStatus.CANCELLED.value]
        else:
            requests = all_requests

        # Статистика
        total_amount = sum(float(r.amount.replace(" ", "").replace(",", ".")) for r in all_requests if r.status == PaymentRequestStatus.PAID.value)
        pending_count = len([r for r in all_requests if r.status == PaymentRequestStatus.PENDING.value])

        content = Div(
            # Статистика
            Div(
                stat_item("Всего запросов", str(len(all_requests)), "📊"),
                stat_item("Ожидает оплаты", str(pending_count), "⏳"),
                stat_item("Оплачено всего", f"{total_amount:,.0f} ₽", "💰"),
                cls="stats stats-vertical lg:stats-horizontal shadow w-full mb-4"
            ),

            # Фильтры
            card("Фильтры", filter_tabs(filter_status)),

            # Таблица
            Div(
                Div(
                    payment_request_table(requests, show_creator=False),
                    cls="card-body p-0"
                ),
                cls="card bg-base-100 shadow-xl my-4"
            ),

            # Форма создания
            card("Создать новый запрос", create_payment_form())
        )

        # Получаем аватар из Telegram
        avatar_url = await get_user_profile_photo_url(bot_token, user.telegram_id)
        if not avatar_url:
            avatar_url = get_fallback_avatar_url(user.display_name)

        return page_layout("Worker Dashboard", content, user.display_name, user.role.value, avatar_url)

    async def owner_dashboard(session, user, role, filter_status, bot_token):
        """Dashboard для Owner/Manager - просмотр всех запросов и статистика"""
        # Получаем все запросы системы
        all_requests = await PaymentRequestCRUD.get_all_payment_requests(session)

        # Фильтруем по статусу
        if filter_status == "pending":
            requests = [r for r in all_requests if r.status == PaymentRequestStatus.PENDING.value]
        elif filter_status == "scheduled":
            requests = [r for r in all_requests if r.status in [
                PaymentRequestStatus.SCHEDULED_TODAY.value,
                PaymentRequestStatus.SCHEDULED_DATE.value
            ]]
        elif filter_status == "paid":
            requests = [r for r in all_requests if r.status == PaymentRequestStatus.PAID.value]
        elif filter_status == "cancelled":
            requests = [r for r in all_requests if r.status == PaymentRequestStatus.CANCELLED.value]
        else:
            requests = all_requests

        # Статистика
        total_amount = sum(float(r.amount.replace(" ", "").replace(",", ".")) for r in all_requests if r.status == PaymentRequestStatus.PAID.value)
        pending_count = len([r for r in all_requests if r.status == PaymentRequestStatus.PENDING.value])
        scheduled_count = len([r for r in all_requests if r.status in [
            PaymentRequestStatus.SCHEDULED_TODAY.value,
            PaymentRequestStatus.SCHEDULED_DATE.value
        ]])

        content = Div(
            # Статистика
            Div(
                stat_item("Всего запросов", str(len(all_requests)), "📊"),
                stat_item("Ожидает оплаты", str(pending_count), "⏳"),
                stat_item("Запланировано", str(scheduled_count), "📅"),
                stat_item("Оплачено всего", f"{total_amount:,.0f} ₽", "💰"),
                cls="stats stats-vertical lg:stats-horizontal shadow w-full mb-4"
            ),

            # Фильтры
            card("Фильтры", filter_tabs(filter_status)),

            # Таблица
            Div(
                Div(
                    payment_request_table(requests, show_creator=True),
                    cls="card-body p-0"
                ),
                cls="card bg-base-100 shadow-xl my-4"
            )
        )

        # Получаем аватар из Telegram
        avatar_url = await get_user_profile_photo_url(bot_token, user.telegram_id)
        if not avatar_url:
            avatar_url = get_fallback_avatar_url(user.display_name)

        return page_layout(f"{role.upper()} Dashboard", content, user.display_name, user.role.value, avatar_url)

    @app.post("/payment/create")
    @require_auth
    async def create_payment_request(sess, title: str, amount: str, comment: str):
        """Создание нового запроса на оплату"""
        user_id = sess.get('user_id')

        async with get_session() as session:
            # Создаем запрос
            payment_request = await PaymentRequestCRUD.create_payment_request(
                session=session,
                created_by_id=user_id,
                title=title,
                amount=amount,
                comment=comment
            )

            logger.info(f"Worker {user_id} создал запрос на оплату #{payment_request.id}")

        # Редирект на dashboard
        return RedirectResponse('/dashboard', status_code=303)

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

    @app.get("/payment/{request_id}")
    @require_auth
    async def payment_detail(sess, request_id: int):
        """Детальная страница запроса на оплату"""
        user_id = sess.get('user_id')
        display_name = sess.get('display_name')
        role = sess.get('role')

        async with get_session() as session:
            current_user = await UserCRUD.get_user_by_id(session, user_id)
            payment_request = await PaymentRequestCRUD.get_payment_request_by_id(session, request_id)

            if not payment_request:
                return RedirectResponse('/dashboard', status_code=303)

            # Worker может видеть только свои запросы
            if role == UserRole.WORKER.value and payment_request.created_by_id != user_id:
                return RedirectResponse('/dashboard', status_code=303)

        content = payment_request_detail(payment_request, role)

        # Получаем аватар из Telegram
        avatar_url = await get_user_profile_photo_url(config.bot_token, current_user.telegram_id) if current_user else None
        if not avatar_url:
            avatar_url = get_fallback_avatar_url(display_name)

        return page_layout(
            f"Запрос на оплату #{request_id}",
            content,
            display_name,
            role,
            avatar_url
        )

    @app.post("/payment/{request_id}/schedule")
    @require_auth
    @require_role(UserRole.OWNER.value, UserRole.MANAGER.value)
    async def schedule_payment(sess, request_id: int, schedule_type: str, scheduled_date: str = None):
        """Планирование оплаты"""
        user_id = sess.get('user_id')

        async with get_session() as session:
            if schedule_type == "today":
                await PaymentRequestCRUD.schedule_payment(
                    session=session,
                    request_id=request_id,
                    processing_by_id=user_id,
                    is_today=True
                )
            else:
                # Парсим дату из строки формата YYYY-MM-DD
                from datetime import datetime
                scheduled_date_obj = datetime.strptime(scheduled_date, "%Y-%m-%d").date()
                await PaymentRequestCRUD.schedule_payment(
                    session=session,
                    request_id=request_id,
                    processing_by_id=user_id,
                    scheduled_date=scheduled_date_obj
                )

            logger.info(f"User {user_id} запланировал оплату запроса #{request_id}")

        return RedirectResponse(f'/payment/{request_id}', status_code=303)

    @app.post("/payment/{request_id}/pay")
    @require_auth
    @require_role(UserRole.OWNER.value, UserRole.MANAGER.value)
    async def mark_payment_as_paid(sess, request_id: int):
        """Отметка запроса как оплаченного (без загрузки файла)"""
        user_id = sess.get('user_id')

        async with get_session() as session:
            # Временно используем пустой file_id, т.к. загрузка файла будет через бот
            # В будущем это можно улучшить
            await PaymentRequestCRUD.mark_as_paid(
                session=session,
                request_id=request_id,
                paid_by_id=user_id,
                payment_proof_file_id="web_payment",  # Временная заглушка
                processing_by_id=user_id
            )

            logger.info(f"User {user_id} отметил запрос #{request_id} как оплаченный")

        return RedirectResponse(f'/payment/{request_id}', status_code=303)

    @app.post("/payment/{request_id}/cancel")
    @require_auth
    async def cancel_payment(sess, request_id: int):
        """Отмена запроса на оплату"""
        user_id = sess.get('user_id')
        role = sess.get('role')

        async with get_session() as session:
            payment_request = await PaymentRequestCRUD.get_payment_request_by_id(session, request_id)

            if not payment_request:
                return RedirectResponse('/dashboard', status_code=303)

            # Worker может отменять только свои запросы
            if role == UserRole.WORKER.value and payment_request.created_by_id != user_id:
                return RedirectResponse('/dashboard', status_code=303)

            await PaymentRequestCRUD.cancel_payment_request(session, request_id)
            logger.info(f"User {user_id} отменил запрос #{request_id}")

        return RedirectResponse('/dashboard', status_code=303)

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
