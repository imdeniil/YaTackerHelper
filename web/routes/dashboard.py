"""Маршруты dashboard для разных ролей"""

import logging
from fasthtml.common import *
from web.database import get_session, UserCRUD, PaymentRequestCRUD
from web.config import WebConfig
from web.components import (
    page_layout, stat_item, payment_request_table,
    create_payment_modal, analytics_modal, advanced_filters
)
from web.telegram_utils import get_user_profile_photo_url, get_fallback_avatar_url
from bot.database.models import UserRole, PaymentRequestStatus
from .decorators import require_auth
from .payments import setup_payment_routes
from .users import setup_user_routes
from .export import setup_export_routes

logger = logging.getLogger(__name__)


def setup_dashboard_routes(app, config: WebConfig):
    """Настраивает маршруты dashboard

    Args:
        app: FastHTML приложение
        config: Конфигурация веб-приложения
    """
    # Регистрируем дочерние маршруты
    setup_payment_routes(app, config)
    setup_user_routes(app, config)
    setup_export_routes(app, config)

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

        # Валидация параметров
        page = max(1, page)
        per_page = per_page if per_page in [10, 20, 25, 50, 100] else 20

        # Извлекаем статусы из query string
        try:
            statuses = request.query_params.getlist('status') if hasattr(request, 'query_params') else []
        except:
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
                return await _worker_dashboard(
                    session, user, statuses, search, date_from, date_to, date_type,
                    amount_min_float, amount_max_float, page, per_page, config.bot_token
                )
            elif role in [UserRole.OWNER.value, UserRole.MANAGER.value]:
                return await _owner_dashboard(
                    session, user, role, statuses, search, date_from, date_to, date_type,
                    amount_min_float, amount_max_float, creator_id, page, per_page, config.bot_token
                )

        # Fallback
        return RedirectResponse('/login', status_code=303)


async def _worker_dashboard(
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
    total_pages = (total_items + per_page - 1) // per_page

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
        'filter_status': 'all'
    }

    # Статистика для модального окна
    stats_items = [
        stat_item("Всего запросов", str(len(all_requests)), "📊"),
        stat_item("Ожидает оплаты", str(pending_count), "⏳"),
        stat_item("Оплачено всего", f"{total_amount:,.0f} ₽", "💰")
    ]

    content = Div(
        # Расширенные фильтры
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
            cls="card bg-base-100 shadow-xl mb-4"
        ),

        # Таблица с пагинацией
        Div(
            Div(
                payment_request_table(requests, show_creator=False, pagination_data=pagination_data),
                cls="card-body p-3"
            ),
            cls="card bg-base-100 shadow-xl mb-4"
        ),

        # Модальное окно создания
        create_payment_modal(user_role=user.role.value),

        # Модальное окно аналитики
        analytics_modal(stats_items)
    )

    # Получаем аватар из Telegram
    avatar_url = await get_user_profile_photo_url(bot_token, user.telegram_id)
    if not avatar_url:
        avatar_url = get_fallback_avatar_url(user.display_name)

    return page_layout("Worker Dashboard", content, user.display_name, user.role.value, avatar_url)


async def _owner_dashboard(
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
    total_pages = (total_items + per_page - 1) // per_page

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
        'filter_status': 'all'
    }

    # Статистика для модального окна
    stats_items = [
        stat_item("Всего запросов", str(len(all_requests)), "📊"),
        stat_item("Ожидает оплаты", str(pending_count), "⏳"),
        stat_item("Запланировано", str(scheduled_count), "📅"),
        stat_item("Оплачено всего", f"{total_amount:,.0f} ₽", "💰")
    ]

    content = Div(
        # Расширенные фильтры
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
            cls="card bg-base-100 shadow-xl mb-4"
        ),

        # Таблица с пагинацией
        Div(
            Div(
                payment_request_table(requests, show_creator=True, pagination_data=pagination_data),
                cls="card-body p-3"
            ),
            cls="card bg-base-100 shadow-xl mb-4"
        ),

        # Модальное окно создания
        create_payment_modal(user_role=role),

        # Модальное окно аналитики
        analytics_modal(stats_items)
    )

    # Получаем аватар из Telegram
    avatar_url = await get_user_profile_photo_url(bot_token, user.telegram_id)
    if not avatar_url:
        avatar_url = get_fallback_avatar_url(user.display_name)

    return page_layout(f"{role.upper()} Dashboard", content, user.display_name, user.role.value, avatar_url)
