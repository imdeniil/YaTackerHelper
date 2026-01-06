"""Основной файл запуска Telegram бота."""

import os
import asyncio
import logging
import argparse
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram_dialog import setup_dialogs

from bot.config import BotConfig
from bot.handlers import commands_router, payment_callbacks_router
from bot.dialogs import (
    main_menu_dialog,
    clone_project_dialog,
    user_management_dialog,
    user_settings_dialog,
    payment_request_creation_dialog,
    my_payment_requests_dialog,
    all_payment_requests_dialog,
)
from bot.middlewares import AuthMiddleware, MessageCleanupMiddleware, unknown_intent_router
from bot.database import init_db, init_default_owners
from bot.database.database import engine
from bot.database.models import Base
from bot.services import start_scheduler, shutdown_scheduler

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Предотвратить дублирование логов YaTrackerApi
# Причина: библиотека YaTrackerApi имеет свой handler, а propagate=True
# передает логи еще и в root logger (от basicConfig), что дает дублирование
# Решение: отключаем propagate, чтобы логи не шли в root logger
ya_tracker_logger = logging.getLogger("YaTrackerApi")
ya_tracker_logger.propagate = False


async def reset_db():
    """Удаляет и пересоздает все таблицы БД."""
    logger.warning("⚠️  ВНИМАНИЕ: Это удалит все данные в базе!")
    logger.warning("Для подтверждения используйте: --reset-db --confirm")
    logger.info("Операция отменена")


async def reset_db_confirmed():
    """Удаляет и пересоздает все таблицы БД (подтверждено)."""
    logger.warning("⚠️  Начинается сброс базы данных...")

    logger.info("🗑️  Удаление существующих таблиц...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    logger.info("✅ Таблицы удалены")

    logger.info("🔧 Создание новых таблиц...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("✅ Таблицы созданы")

    logger.info("🎉 База данных пересоздана!")
    logger.info("💡 Владельцы будут созданы автоматически из .env при запуске бота")

    # Предупреждение о необходимости удалить RESET_DB из .env
    if os.getenv("RESET_DB"):
        logger.warning("⚠️  ВАЖНО: Удалите RESET_DB=true из .env файла!")
        logger.warning("⚠️  Иначе БД будет сброшена при каждом перезапуске контейнера!")


async def main(reset_database: bool = False, confirm_reset: bool = False, continue_after_reset: bool = False):
    """Основная функция запуска бота.

    Args:
        reset_database: Флаг сброса БД
        confirm_reset: Подтверждение сброса
        continue_after_reset: Продолжить запуск бота после сброса (для Docker)
    """
    # Обработка сброса БД
    if reset_database:
        if confirm_reset:
            await reset_db_confirmed()
        else:
            await reset_db()

        # Если сброс через CLI - завершаем, если через env - продолжаем
        if not continue_after_reset:
            return

    logger.info("Запуск бота...")

    # Загрузка конфигурации
    try:
        config = BotConfig.from_env()
        logger.info("✅ Конфигурация загружена")
    except ValueError as e:
        logger.error(f"❌ Ошибка конфигурации: {e}")
        return

    # Инициализация бота и диспетчера
    bot = Bot(
        token=config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # Сохранение конфигурации в данных диспетчера
    dp["config"] = config

    # Инициализация базы данных
    await init_db()
    logger.info("✅ База данных инициализирована")

    # Создание дефолтных владельцев (если не существуют)
    await init_default_owners()

    # Регистрация middleware
    dp.update.middleware(AuthMiddleware())
    dp.message.middleware(MessageCleanupMiddleware())
    logger.info("✅ Middleware зарегистрированы")

    # Регистрация роутеров
    dp.include_router(unknown_intent_router)  # Error handler должен быть первым
    dp.include_router(commands_router)
    dp.include_router(payment_callbacks_router)

    # Регистрация диалогов
    dp.include_router(main_menu_dialog)
    dp.include_router(clone_project_dialog)
    dp.include_router(user_management_dialog)
    dp.include_router(user_settings_dialog)
    dp.include_router(payment_request_creation_dialog)
    dp.include_router(my_payment_requests_dialog)
    dp.include_router(all_payment_requests_dialog)

    # Настройка aiogram-dialog
    setup_dialogs(dp)

    logger.info("✅ Все роутеры и диалоги зарегистрированы")

    # Удаление вебхуков (если были)
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("✅ Вебхуки удалены")
    except Exception as e:
        logger.warning(f"⚠️ Не удалось удалить вебхуки: {e}")
        logger.info("Продолжаем запуск...")

    # Запуск scheduler для напоминаний
    start_scheduler(bot)

    logger.info("🚀 Бот запущен и готов к работе!")

    # Запуск polling
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        # Останавливаем scheduler
        shutdown_scheduler()
        await bot.session.close()
        logger.info("👋 Бот остановлен")


if __name__ == "__main__":
    # Парсинг аргументов командной строки
    parser = argparse.ArgumentParser(
        description="YaTackerHelper Telegram Bot",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  python main.py                      # Запуск бота
  python main.py --reset-db           # Показать предупреждение о сбросе БД
  python main.py --reset-db --confirm # Сбросить базу данных

  # Для Docker: установи RESET_DB=true в .env для сброса при запуске
        """,
    )
    parser.add_argument(
        "--reset-db",
        action="store_true",
        help="Удалить и пересоздать все таблицы базы данных (требует --confirm)",
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Подтверждение опасных операций (например, сброса БД)",
    )

    args = parser.parse_args()

    # Проверка переменной окружения RESET_DB для Docker
    reset_db_env = os.getenv("RESET_DB", "").lower() in ("true", "1", "yes")

    # Если RESET_DB=true в окружении, автоматически подтверждаем сброс и продолжаем запуск
    if reset_db_env:
        logger.warning("🔥 RESET_DB=true обнаружен в переменных окружения")
        logger.warning("🔥 База данных будет сброшена при запуске!")
        reset_database = True
        confirm_reset = True
        continue_after_reset = True
    else:
        reset_database = args.reset_db
        confirm_reset = args.confirm
        continue_after_reset = False

    try:
        asyncio.run(main(
            reset_database=reset_database,
            confirm_reset=confirm_reset,
            continue_after_reset=continue_after_reset
        ))
    except KeyboardInterrupt:
        logger.info("⚠️ Бот остановлен пользователем")
