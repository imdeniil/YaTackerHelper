"""Основное веб-приложение FastHTML для YaTackerHelper"""

import logging
import os
from pathlib import Path
from fasthtml.common import *
from starlette.staticfiles import StaticFiles
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

# Настройка статических файлов
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


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
        timeout_keep_alive=30,
        # h11_max_incomplete_event_size увеличивает лимит для загрузки файлов
        h11_max_incomplete_event_size=26214400,  # 25MB
    )


if __name__ == "__main__":
    serve()
