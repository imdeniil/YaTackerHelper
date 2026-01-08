"""Основной файл запуска Telegram бота."""

import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram_dialog import setup_dialogs

from bot.config import BotConfig
from bot.handlers import commands_router, pending_list_router, testing_router
from bot.dialogs import (
    main_menu_dialog,
    clone_project_dialog,
    project_info_dialog,
)

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def main():
    """Основная функция запуска бота."""
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

    # Регистрация роутеров
    dp.include_router(commands_router)
    dp.include_router(pending_list_router)
    dp.include_router(testing_router)

    # Регистрация диалогов
    dp.include_router(main_menu_dialog)
    dp.include_router(clone_project_dialog)
    dp.include_router(project_info_dialog)

    # Настройка aiogram-dialog
    setup_dialogs(dp)

    logger.info("✅ Все роутеры и диалоги зарегистрированы")

    # Удаление вебхуков (если были)
    await bot.delete_webhook(drop_pending_updates=True)

    logger.info("🚀 Бот запущен и готов к работе!")

    # Запуск polling
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()
        logger.info("👋 Бот остановлен")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("⚠️ Бот остановлен пользователем")
