"""Маршруты dashboard для разных ролей"""

import logging
from functools import wraps
from fasthtml.common import *
from web.database import get_session, UserCRUD, PaymentRequestCRUD
from web.config import WebConfig
from web.components import (
    page_layout, stat_item, payment_request_table,
    create_payment_form, filter_tabs, user_table, card,
    payment_request_detail, user_edit_form, user_create_form,
    advanced_filters
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
    async def dashboard(
        sess,
        request,
        filter: str = "all",
        search: str = "",
        date_from: str = "",
        date_to: str = "",
        date_type: str = "created",
        amount_min: str = "",
        amount_max: str = "",
        creator_id: int = None,
        page: int = 1,
        per_page: int = 20
    ):
        """Главная страница dashboard - роутинг по ролям"""
        user_id = sess.get('user_id')
        role = sess.get('role')
        display_name = sess.get('display_name')

        # Валидация параметров
        page = max(1, page)  # Минимум 1
        per_page = per_page if per_page in [10, 25, 50, 100] else 20

        # Извлекаем статусы из query string (FastHTML не парсит списки автоматически)
        # Пробуем через query_params.getlist (Starlette)
        try:
            statuses = request.query_params.getlist('status') if hasattr(request, 'query_params') else []
        except:
            # Fallback - парсим вручную
            from urllib.parse import parse_qs
            query_string = str(request.url.query) if request.url.query else ""
            query_params = parse_qs(query_string)
            statuses = query_params.get('status', [])

        logger.info(f"Dashboard request - Statuses: {statuses}, Type: {type(statuses)}")

        amount_min_float = float(amount_min) if amount_min else None
        amount_max_float = float(amount_max) if amount_max else None

        # Получаем пользователя из БД для актуальных данных
        async with get_session() as session:
            user = await UserCRUD.get_user_by_id(session, user_id)

            if not user:
                sess.clear()
                return RedirectResponse('/login', status_code=303)

            # Роутинг по ролям
            if role == UserRole.WORKER.value:
                return await worker_dashboard(
                    session, user, statuses, search, date_from, date_to, date_type,
                    amount_min_float, amount_max_float, page, per_page, config.bot_token
                )
            elif role in [UserRole.OWNER.value, UserRole.MANAGER.value]:
                return await owner_dashboard(
                    session, user, role, statuses, search, date_from, date_to, date_type,
                    amount_min_float, amount_max_float, creator_id, page, per_page, config.bot_token
                )

        # Fallback
        return RedirectResponse('/login', status_code=303)

    async def worker_dashboard(
        session, user, statuses, search, date_from, date_to, date_type,
        amount_min, amount_max, page, per_page, bot_token
    ):
        """Dashboard для Worker - создание и просмотр своих запросов"""
        # Подсчет общего количества записей с учетом фильтров
        total_items = await PaymentRequestCRUD.count_payment_requests_advanced(
            session=session,
            user_id=user.id,
            statuses=statuses if len(statuses) > 0 else None,
            search_query=search if search else None,
            date_from=date_from if date_from else None,
            date_to=date_to if date_to else None,
            date_type=date_type,
            amount_min=amount_min,
            amount_max=amount_max
        )

        # Подсчет страниц
        total_pages = (total_items + per_page - 1) // per_page  # Округление вверх

        # Получаем запросы с расширенными фильтрами
        skip = (page - 1) * per_page
        requests = await PaymentRequestCRUD.get_payment_requests_advanced(
            session=session,
            user_id=user.id,
            statuses=statuses if len(statuses) > 0 else None,
            search_query=search if search else None,
            date_from=date_from if date_from else None,
            date_to=date_to if date_to else None,
            date_type=date_type,
            amount_min=amount_min,
            amount_max=amount_max,
            skip=skip,
            limit=per_page
        )

        # Статистика (на основе всех запросов пользователя, без фильтров)
        all_requests = await PaymentRequestCRUD.get_payment_requests_advanced(
            session, user_id=user.id, skip=0, limit=10000
        )
        total_amount = sum(float(r.amount.replace(" ", "").replace(",", ".")) for r in all_requests if r.status == PaymentRequestStatus.PAID.value)
        pending_count = len([r for r in all_requests if r.status == PaymentRequestStatus.PENDING.value])

        # Данные для пагинации
        pagination_data = {
            'current_page': page,
            'total_pages': total_pages,
            'per_page': per_page,
            'total_items': total_items,
            'filter_status': 'all'  # Для обратной совместимости
        }

        content = Div(
            # Статистика
            Div(
                stat_item("Всего запросов", str(len(all_requests)), "📊"),
                stat_item("Ожидает оплаты", str(pending_count), "⏳"),
                stat_item("Оплачено всего", f"{total_amount:,.0f} ₽", "💰"),
                cls="stats stats-vertical lg:stats-horizontal shadow w-full mb-4"
            ),

            # Расширенные фильтры (без заголовка)
            Div(
                Div(
                    advanced_filters(
                        current_statuses=statuses,
                        search_query=search,
                        date_from=date_from,
                        date_to=date_to,
                        date_type=date_type,
                        amount_min=str(amount_min) if amount_min else "",
                        amount_max=str(amount_max) if amount_max else "",
                        show_creator_filter=False,
                        per_page=per_page
                    ),
                    cls="card-body"
                ),
                cls="card bg-base-100 shadow-xl my-4"
            ),

            # Таблица с пагинацией
            Div(
                Div(
                    payment_request_table(requests, show_creator=False, pagination_data=pagination_data),
                    cls="card-body p-3"
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

    async def owner_dashboard(
        session, user, role, statuses, search, date_from, date_to, date_type,
        amount_min, amount_max, creator_id, page, per_page, bot_token
    ):
        """Dashboard для Owner/Manager - просмотр всех запросов и статистика"""
        # Получаем список всех пользователей для фильтра
        all_users = await UserCRUD.get_all_users(session)

        # Подсчет общего количества записей с учетом фильтров
        total_items = await PaymentRequestCRUD.count_payment_requests_advanced(
            session=session,
            statuses=statuses if len(statuses) > 0 else None,
            search_query=search if search else None,
            date_from=date_from if date_from else None,
            date_to=date_to if date_to else None,
            date_type=date_type,
            amount_min=amount_min,
            amount_max=amount_max,
            creator_id=creator_id
        )

        # Подсчет страниц
        total_pages = (total_items + per_page - 1) // per_page  # Округление вверх

        # Получаем запросы с расширенными фильтрами
        skip = (page - 1) * per_page
        requests = await PaymentRequestCRUD.get_payment_requests_advanced(
            session=session,
            statuses=statuses if len(statuses) > 0 else None,
            search_query=search if search else None,
            date_from=date_from if date_from else None,
            date_to=date_to if date_to else None,
            date_type=date_type,
            amount_min=amount_min,
            amount_max=amount_max,
            creator_id=creator_id,
            skip=skip,
            limit=per_page
        )

        # Статистика (на основе всех запросов системы, без фильтров)
        all_requests = await PaymentRequestCRUD.get_payment_requests_advanced(
            session, skip=0, limit=10000
        )
        total_amount = sum(float(r.amount.replace(" ", "").replace(",", ".")) for r in all_requests if r.status == PaymentRequestStatus.PAID.value)
        pending_count = len([r for r in all_requests if r.status == PaymentRequestStatus.PENDING.value])
        scheduled_count = len([r for r in all_requests if r.status in [
            PaymentRequestStatus.SCHEDULED_TODAY.value,
            PaymentRequestStatus.SCHEDULED_DATE.value
        ]])

        # Данные для пагинации
        pagination_data = {
            'current_page': page,
            'total_pages': total_pages,
            'per_page': per_page,
            'total_items': total_items,
            'filter_status': 'all'  # Для обратной совместимости
        }

        content = Div(
            # Статистика
            Div(
                stat_item("Всего запросов", str(len(all_requests)), "📊"),
                stat_item("Ожидает оплаты", str(pending_count), "⏳"),
                stat_item("Запланировано", str(scheduled_count), "📅"),
                stat_item("Оплачено всего", f"{total_amount:,.0f} ₽", "💰"),
                cls="stats stats-vertical lg:stats-horizontal shadow w-full mb-4"
            ),

            # Расширенные фильтры (без заголовка)
            Div(
                Div(
                    advanced_filters(
                        current_statuses=statuses,
                        search_query=search,
                        date_from=date_from,
                        date_to=date_to,
                        date_type=date_type,
                        amount_min=str(amount_min) if amount_min else "",
                        amount_max=str(amount_max) if amount_max else "",
                        creator_id=creator_id,
                        users=all_users,
                        show_creator_filter=True,
                        per_page=per_page
                    ),
                    cls="card-body"
                ),
                cls="card bg-base-100 shadow-xl my-4"
            ),

            # Таблица с пагинацией
            Div(
                Div(
                    payment_request_table(requests, show_creator=True, pagination_data=pagination_data),
                    cls="card-body p-3"
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

    @app.get("/payment/{request_id}/download/invoice")
    @require_auth
    async def download_invoice(sess, request_id: int):
        """Скачивание счета"""
        user_id = sess.get('user_id')
        role = sess.get('role')

        async with get_session() as session:
            payment_request = await PaymentRequestCRUD.get_payment_request_by_id(session, request_id)

            if not payment_request:
                return RedirectResponse('/dashboard', status_code=303)

            # Worker может скачивать только свои файлы
            if role == UserRole.WORKER.value and payment_request.created_by_id != user_id:
                return RedirectResponse('/dashboard', status_code=303)

            if not payment_request.invoice_file_id:
                return RedirectResponse(f'/payment/{request_id}', status_code=303)

            # Получаем URL файла из Telegram
            import httpx
            async with httpx.AsyncClient() as client:
                # Получаем информацию о файле
                file_response = await client.get(
                    f"https://api.telegram.org/bot{config.bot_token}/getFile",
                    params={"file_id": payment_request.invoice_file_id}
                )

                if file_response.status_code != 200:
                    logger.error(f"Не удалось получить файл счета для запроса #{request_id}")
                    return RedirectResponse(f'/payment/{request_id}', status_code=303)

                file_data = file_response.json()
                if not file_data.get("ok"):
                    return RedirectResponse(f'/payment/{request_id}', status_code=303)

                file_path = file_data["result"]["file_path"]
                file_url = f"https://api.telegram.org/file/bot{config.bot_token}/{file_path}"

                # Редирект на файл
                return RedirectResponse(file_url, status_code=303)

    @app.get("/payment/{request_id}/download/proof")
    @require_auth
    async def download_payment_proof(sess, request_id: int):
        """Скачивание платежки"""
        user_id = sess.get('user_id')
        role = sess.get('role')

        async with get_session() as session:
            payment_request = await PaymentRequestCRUD.get_payment_request_by_id(session, request_id)

            if not payment_request:
                return RedirectResponse('/dashboard', status_code=303)

            # Worker может скачивать только свои файлы
            if role == UserRole.WORKER.value and payment_request.created_by_id != user_id:
                return RedirectResponse('/dashboard', status_code=303)

            if not payment_request.payment_proof_file_id:
                return RedirectResponse(f'/payment/{request_id}', status_code=303)

            # Получаем URL файла из Telegram
            import httpx
            async with httpx.AsyncClient() as client:
                # Получаем информацию о файле
                file_response = await client.get(
                    f"https://api.telegram.org/bot{config.bot_token}/getFile",
                    params={"file_id": payment_request.payment_proof_file_id}
                )

                if file_response.status_code != 200:
                    logger.error(f"Не удалось получить файл платежки для запроса #{request_id}")
                    return RedirectResponse(f'/payment/{request_id}', status_code=303)

                file_data = file_response.json()
                if not file_data.get("ok"):
                    return RedirectResponse(f'/payment/{request_id}', status_code=303)

                file_path = file_data["result"]["file_path"]
                file_url = f"https://api.telegram.org/file/bot{config.bot_token}/{file_path}"

                # Редирект на файл
                return RedirectResponse(file_url, status_code=303)
