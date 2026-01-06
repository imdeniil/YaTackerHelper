"""Маршруты dashboard для разных ролей"""

import logging
from functools import wraps
from fasthtml.common import *
from web.database import get_session, UserCRUD, PaymentRequestCRUD
from web.config import WebConfig
from web.components import (
    page_layout, stats_group, payment_request_table,
    create_payment_form, filter_tabs, user_table
)
from bot.database.models import UserRole, PaymentRequestStatus

logger = logging.getLogger(__name__)


def require_auth(f):
    """Декоратор для проверки авторизации"""
    @wraps(f)
    async def wrapper(sess, **kwargs):
        user_id = sess.get('user_id')
        if not user_id:
            return RedirectResponse('/login', status_code=303)
        return await f(sess, **kwargs)
    return wrapper


def require_role(*allowed_roles):
    """Декоратор для проверки роли"""
    def decorator(f):
        @wraps(f)
        async def wrapper(sess, **kwargs):
            role = sess.get('role')
            if role not in allowed_roles:
                return RedirectResponse('/dashboard', status_code=303)
            return await f(sess, **kwargs)
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
                return await worker_dashboard(session, user, filter)
            elif role in [UserRole.OWNER.value, UserRole.MANAGER.value]:
                return await owner_dashboard(session, user, role, filter)

        # Fallback
        return RedirectResponse('/login', status_code=303)

    async def worker_dashboard(session, user, filter_status):
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
            H1(f"Привет, {user.display_name}!", cls="text-2xl font-bold mb-6"),

            # Статистика
            stats_group([
                ("Всего запросов", str(len(all_requests)), ""),
                ("Ожидает оплаты", str(pending_count), "На рассмотрении"),
                ("Оплачено", f"{total_amount:,.0f} ₽", "Общая сумма"),
            ]),

            # Форма создания
            Div(
                H2("Создать новый запрос", cls="text-xl font-bold mb-4"),
                create_payment_form(),
                cls="mt-8"
            ),

            # Список запросов
            Div(
                H2("Мои запросы", cls="text-xl font-bold mb-4"),
                filter_tabs(filter_status),
                payment_request_table(requests, show_creator=False),
                cls="mt-8"
            )
        )

        return page_layout("Worker Dashboard", content, user.display_name, user.role.value)

    async def owner_dashboard(session, user, role, filter_status):
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

        # Кнопка управления пользователями для Owner
        manage_users_btn = None
        if role == UserRole.OWNER.value:
            manage_users_btn = Div(
                A("Управление пользователями", href="/users", cls="btn btn-outline btn-sm"),
                cls="flex justify-end mb-4"
            )

        content = Div(
            Div(
                H1(f"Привет, {user.display_name}!", cls="text-2xl font-bold"),
                manage_users_btn,
                cls="flex items-center justify-between mb-6"
            ),

            # Статистика
            stats_group([
                ("Всего запросов", str(len(all_requests)), "За всё время"),
                ("Ожидает", str(pending_count), "Требует действий"),
                ("Запланировано", str(scheduled_count), "В работе"),
                ("Оплачено", f"{total_amount:,.0f} ₽", "Общая сумма"),
            ]),

            # Список всех запросов
            Div(
                H2("Все запросы на оплату", cls="text-xl font-bold mb-4"),
                filter_tabs(filter_status),
                payment_request_table(requests, show_creator=True),
                cls="mt-8"
            )
        )

        return page_layout(f"{role.upper()} Dashboard", content, user.display_name, user.role.value)

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
        display_name = sess.get('display_name')
        role = sess.get('role')

        async with get_session() as session:
            users = await UserCRUD.get_all_users(session)

        content = Div(
            Div(
                H1("Управление пользователями", cls="text-2xl font-bold"),
                A("← Назад", href="/dashboard", cls="btn btn-ghost btn-sm"),
                cls="flex justify-between items-center mb-6"
            ),

            user_table(users)
        )

        return page_layout("Пользователи", content, display_name, role)
