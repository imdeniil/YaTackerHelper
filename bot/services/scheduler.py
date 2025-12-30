"""Scheduler для автоматических задач бота"""

import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from pytz import timezone
from aiogram import Bot

from .payment_reminders import (
    send_reminder_scheduled_today,
    send_reminder_scheduled_date,
    rollover_scheduled_today,
)

logger = logging.getLogger(__name__)

# Timezone Moscow
MSK = timezone('Europe/Moscow')

# Global scheduler instance
scheduler: AsyncIOScheduler | None = None


def start_scheduler(bot: Bot):
    """Запускает scheduler с задачами для напоминаний об оплате

    Args:
        bot: Instance бота для отправки сообщений
    """
    global scheduler

    if scheduler is not None:
        logger.warning("Scheduler already running")
        return

    # Создаем scheduler
    scheduler = AsyncIOScheduler(timezone=MSK)

    # Задача 1: Напоминание в 18:00 МСК для SCHEDULED_TODAY
    scheduler.add_job(
        send_reminder_scheduled_today,
        trigger=CronTrigger(hour=18, minute=0, timezone=MSK),
        args=[bot],
        id='reminder_scheduled_today',
        name='Reminder for SCHEDULED_TODAY payments at 18:00 MSK',
        replace_existing=True,
    )
    logger.info("Scheduled reminder_scheduled_today at 18:00 MSK")

    # Задача 2: Напоминание в 10:00 МСК для SCHEDULED_DATE (сегодня)
    scheduler.add_job(
        send_reminder_scheduled_date,
        trigger=CronTrigger(hour=10, minute=0, timezone=MSK),
        args=[bot],
        id='reminder_scheduled_date',
        name='Reminder for SCHEDULED_DATE payments at 10:00 MSK',
        replace_existing=True,
    )
    logger.info("Scheduled reminder_scheduled_date at 10:00 MSK")

    # Задача 3: Rollover в 10:00 МСК для неоплаченных SCHEDULED_TODAY
    scheduler.add_job(
        rollover_scheduled_today,
        trigger=CronTrigger(hour=10, minute=0, timezone=MSK),
        args=[bot],
        id='rollover_scheduled_today',
        name='Rollover SCHEDULED_TODAY payments at 10:00 MSK',
        replace_existing=True,
    )
    logger.info("Scheduled rollover_scheduled_today at 10:00 MSK")

    # Запускаем scheduler
    scheduler.start()
    logger.info("✅ Scheduler started successfully")


def shutdown_scheduler():
    """Останавливает scheduler"""
    global scheduler

    if scheduler is None:
        logger.warning("Scheduler not running")
        return

    scheduler.shutdown()
    scheduler = None
    logger.info("✅ Scheduler stopped")
