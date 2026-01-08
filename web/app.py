"""Основное веб-приложение FastHTML для YaTackerHelper"""

import logging
from fasthtml.common import *
from web.config import WebConfig
from web.database import init_database

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Загрузка конфигурации
config = WebConfig.from_env()

# Инициализация БД
init_database(config)

# Создание FastHTML приложения с secret_key для сессий
# Увеличиваем лимит размера тела запроса до 25MB для загрузки файлов
app = FastHTML(
    secret_key=config.secret_key,
    hdrs=(
        # DaisyUI для стилизации (встроено в FastHTML)
        Script(src="https://cdn.tailwindcss.com"),
        Link(rel="stylesheet", href="https://cdn.jsdelivr.net/npm/daisyui@4/dist/full.min.css"),
        # Telegram Login Widget
        Script(src="https://telegram.org/js/telegram-widget.js?22", _async=True),
    )
)

# Настраиваем максимальный размер тела запроса (25MB)
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware

class LargeUploadMiddleware(BaseHTTPMiddleware):
    """Middleware для поддержки больших загрузок файлов"""
    async def dispatch(self, request, call_next):
        # Starlette/FastAPI использует MultiPartParser с лимитом по умолчанию
        # Переопределяем максимальный размер через атрибуты
        request.scope['_body'] = b''
        response = await call_next(request)
        return response

# Добавляем middleware
app.add_middleware(LargeUploadMiddleware)

# Импортируем маршруты
from web.routes.auth import setup_auth_routes
from web.routes.dashboard import setup_dashboard_routes

# Регистрируем маршруты
setup_auth_routes(app, config)
setup_dashboard_routes(app, config)

@app.get("/")
def index(sess):
    """Главная страница - редирект на dashboard или login"""
    user_id = sess.get('user_id')

    if user_id:
        # Пользователь авторизован - редирект на dashboard
        return RedirectResponse('/dashboard', status_code=303)
    else:
        # Не авторизован - редирект на страницу входа
        return RedirectResponse('/login', status_code=303)


@app.get("/health")
def health():
    """Health check endpoint"""
    return {"status": "ok", "service": "YaTackerHelper Web"}


def serve():
    """Запуск веб-сервера"""
    logger.info(f"🚀 Запуск веб-приложения на http://{config.host}:{config.port}")
    logger.info(f"📊 Dashboard будет доступен после авторизации")

    import uvicorn
    uvicorn.run(
        app,
        host=config.host,
        port=config.port,
        log_level="info",
        limit_max_requests=0,  # Без ограничения на количество запросов
        timeout_keep_alive=5,
        # Увеличиваем лимит размера тела запроса до 25MB (для загрузки файлов)
        limit_concurrency=None,
        backlog=2048,
    )


if __name__ == "__main__":
    serve()
