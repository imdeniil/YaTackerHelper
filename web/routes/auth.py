"""Маршруты авторизации через Telegram Login Widget"""

import hashlib
import hmac
import logging
from fasthtml.common import *
from web.database import get_session, UserCRUD
from web.config import WebConfig

logger = logging.getLogger(__name__)


def verify_telegram_auth(auth_data: dict, bot_token: str) -> bool:
    """Проверяет подлинность данных от Telegram Login Widget

    Args:
        auth_data: Данные от Telegram (id, first_name, last_name, username, hash, etc.)
        bot_token: Токен бота

    Returns:
        True если данные подлинные, False иначе
    """
    check_hash = auth_data.get('hash')
    if not check_hash:
        return False

    # Удаляем hash из данных для проверки
    data_check_arr = []
    for key, value in sorted(auth_data.items()):
        if key != 'hash':
            data_check_arr.append(f'{key}={value}')

    data_check_string = '\n'.join(data_check_arr)

    # Создаем секретный ключ из токена бота
    secret_key = hashlib.sha256(bot_token.encode()).digest()

    # Вычисляем hash
    calculated_hash = hmac.new(
        secret_key,
        data_check_string.encode(),
        hashlib.sha256
    ).hexdigest()

    return calculated_hash == check_hash


def setup_auth_routes(app, config: WebConfig):
    """Настраивает маршруты авторизации

    Args:
        app: FastHTML приложение
        config: Конфигурация веб-приложения
    """

    @app.get("/login")
    def login_page(sess):
        """Страница входа через Telegram"""
        # Если уже авторизован - редирект на dashboard
        if sess.get('user_id'):
            return RedirectResponse('/dashboard', status_code=303)

        return Html(
            Head(
                Title("Вход - YaTackerHelper"),
                Meta(charset="utf-8"),
                Meta(name="viewport", content="width=device-width, initial-scale=1"),
                Style("""
                    body {
                        margin: 0;
                        min-height: 100vh;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        background: #f5f5f5;
                    }
                """),
            ),
            Body(
                # Telegram Login Widget
                Script(f"""
                    window.onTelegramAuth = function(user) {{
                        const form = document.createElement('form');
                        form.method = 'POST';
                        form.action = '/auth/telegram';

                        for (const key in user) {{
                            const input = document.createElement('input');
                            input.type = 'hidden';
                            input.name = key;
                            input.value = user[key];
                            form.appendChild(input);
                        }}

                        document.body.appendChild(form);
                        form.submit();
                    }};
                """),
                Script(
                    src="https://telegram.org/js/telegram-widget.js?22",
                    data_telegram_login="bmyatrackerv2bot",
                    data_size="large",
                    data_onauth="onTelegramAuth(user)",
                    data_request_access="write",
                    _async=True
                ),
            )
        )

    @app.post("/auth/telegram")
    async def telegram_auth(
        sess,
        id: str = None,
        first_name: str = None,
        last_name: str = None,
        username: str = None,
        photo_url: str = None,
        auth_date: str = None,
        hash: str = None
    ):
        """Обработчик авторизации через Telegram

        Проверяет подлинность данных и создает сессию
        """
        # Собираем все данные от Telegram
        auth_data = {
            'id': id,
            'first_name': first_name,
            'hash': hash,
            'auth_date': auth_date,
        }

        # Добавляем опциональные поля если они есть
        if last_name:
            auth_data['last_name'] = last_name
        if username:
            auth_data['username'] = username
        if photo_url:
            auth_data['photo_url'] = photo_url

        # Проверяем подлинность данных
        if not verify_telegram_auth(auth_data, config.bot_token):
            logger.warning(f"Failed Telegram auth attempt for ID {id}")
            return Html(
                Body(
                    Div(
                        Div(
                            H2("Ошибка авторизации", cls="text-2xl font-bold text-error mb-4"),
                            P("Не удалось проверить подлинность данных от Telegram.", cls="mb-4"),
                            A("Попробовать снова", href="/login", cls="btn btn-primary"),
                            cls="card bg-base-100 shadow-xl p-8"
                        ),
                        cls="hero min-h-screen bg-base-200"
                    )
                )
            )

        telegram_id = int(id)

        # Ищем пользователя в БД
        async with get_session() as session:
            user = await UserCRUD.get_user_by_telegram_id(session, telegram_id)

            if not user:
                # Пользователь не найден в системе
                logger.warning(f"Telegram user {telegram_id} (@{username}) not found in database")
                return Html(
                    Body(
                        Div(
                            Div(
                                H2("Доступ запрещен", cls="text-2xl font-bold text-error mb-4"),
                                P("Ваш аккаунт не найден в системе.", cls="mb-2"),
                                P("Обратитесь к администратору для получения доступа.", cls="mb-4 text-sm text-gray-600"),
                                P(f"Ваш Telegram ID: {telegram_id}", cls="text-xs text-gray-500 mb-4"),
                                A("Назад", href="/login", cls="btn btn-primary"),
                                cls="card bg-base-100 shadow-xl p-8"
                            ),
                            cls="hero min-h-screen bg-base-200"
                        )
                    )
                )

            # Обновляем telegram_id пользователя если он еще не был установлен
            if not user.telegram_id:
                await UserCRUD.update_user(session, user.id, telegram_id=telegram_id)

        # Создаем сессию
        sess['user_id'] = user.id
        sess['telegram_id'] = telegram_id
        sess['username'] = username
        sess['display_name'] = user.display_name
        sess['role'] = user.role.value
        sess['is_billing_contact'] = user.is_billing_contact

        logger.info(f"User {user.display_name} (@{username}) logged in successfully")

        # Редирект на dashboard
        return RedirectResponse('/dashboard', status_code=303)

    @app.get("/logout")
    def logout(sess):
        """Выход из системы"""
        sess.clear()
        logger.info("User logged out")
        return RedirectResponse('/login', status_code=303)
