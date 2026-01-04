"""Button handlers для диалога клонирования проекта"""

import asyncio
import time
from aiogram.types import Message, CallbackQuery
from aiogram_dialog import DialogManager, ShowMode
from aiogram_dialog.widgets.kbd import Button, Select
from aiogram_dialog.widgets.input import MessageInput

from bot.states import CloneProject
from src.tracker_client import TrackerClient
from src.project_cloner import ProjectCloner
from .constants import UPDATE_INTERVAL


async def on_project_selected(
    callback: CallbackQuery, widget: Select, manager: DialogManager, item_id: str
):
    """
    Обработчик выбора проекта из списка.

    Args:
        callback: Callback от Select
        widget: Select виджет
        manager: Менеджер диалогов
        item_id: ID выбранного проекта (парсится из Select)
    """
    # item_id это ID проекта который был выбран
    manager.dialog_data["project_id"] = item_id

    # Получаем название проекта из списка
    projects = manager.dialog_data.get("template_projects", [])
    project_name = next(
        (name for name, pid in projects if pid == item_id),
        "Неизвестен"
    )
    manager.dialog_data["project_name"] = project_name

    manager.show_mode = ShowMode.EDIT
    await manager.switch_to(CloneProject.confirm_project)


async def on_confirm_project(
    callback: CallbackQuery, button: Button, manager: DialogManager
):
    """Подтверждение выбранного проекта."""
    manager.show_mode = ShowMode.EDIT
    await manager.switch_to(CloneProject.enter_new_name)


async def on_new_name_input(
    message: Message, widget: MessageInput, manager: DialogManager
):
    """Обработчик ввода нового имени проекта."""
    if not message.text:
        await message.answer("❌ Пожалуйста, отправьте текстовое сообщение")
        return

    new_name = message.text.strip()
    manager.dialog_data["new_name"] = new_name

    # Очищаем queue_step при переходе к выбору очереди
    manager.dialog_data["queue_step"] = ""

    manager.show_mode = ShowMode.EDIT
    await manager.switch_to(CloneProject.enter_queue)


async def on_use_default_queue(
    callback: CallbackQuery, button: Button, manager: DialogManager
):
    """Использовать дефолтную очередь из настроек."""
    user_settings = manager.middleware_data.get("user_settings")
    if user_settings and user_settings.default_queue:
        manager.dialog_data["queue"] = user_settings.default_queue
        manager.show_mode = ShowMode.EDIT
        await manager.switch_to(CloneProject.confirm_clone)


async def on_enter_custom_queue(
    callback: CallbackQuery, button: Button, manager: DialogManager
):
    """Переключиться в режим выбора очереди из списка."""
    manager.dialog_data["queue_step"] = "select_queue_list"
    manager.show_mode = ShowMode.EDIT
    await manager.update({})


async def on_clone_queue_selected(
    callback: CallbackQuery, widget: Select, manager: DialogManager, item_id: str
):
    """Обработка выбора очереди из списка."""
    manager.dialog_data["queue"] = item_id
    manager.show_mode = ShowMode.EDIT
    await manager.switch_to(CloneProject.confirm_clone)


async def on_start_clone(
    callback: CallbackQuery, button: Button, manager: DialogManager
):
    """Запуск процесса клонирования (подход 9: динамическое окно)."""
    # Получаем данные для передачи в фоновую задачу
    project_id = manager.dialog_data.get("project_id")
    new_name = manager.dialog_data.get("new_name")
    queue = manager.dialog_data.get("queue")

    # Инициализируем данные прогресса и устанавливаем флаг клонирования
    manager.dialog_data["is_cloning"] = True
    manager.dialog_data["progress"] = 0
    manager.dialog_data["phase"] = "Инициализация..."

    # ❌ НЕ делаем switch_to! Остаемся на confirm_clone
    # Окно само перерисуется через when условия
    # await manager.switch_to(CloneProject.progress)  # ← УБРАЛИ

    # Создаем BgManager для фоновой задачи
    bg = manager.bg()

    # Запуск фоновой задачи с BgManager
    asyncio.create_task(
        clone_project_background_with_manager(
            manager=bg,
            project_id=project_id,
            new_name=new_name,
            queue=queue
        )
    )


async def on_message_during_clone(
    message: Message,
    widget: MessageInput,
    manager: DialogManager
):
    """Игнорируем сообщения во время клонирования."""
    manager.show_mode = ShowMode.EDIT


async def clone_project_background_with_manager(
    manager: DialogManager,
    project_id: str,
    new_name: str,
    queue: str
):
    """
    Фоновая задача клонирования проекта с использованием BgManager (подход 9).

    Args:
        manager: BgManager для обновления UI
        project_id: ID проекта-шаблона
        new_name: Название нового проекта
        queue: Очередь для задач
    """
    try:
        # Создание клиента Tracker
        async with TrackerClient() as tracker:
            cloner = ProjectCloner(tracker)

            # Throttling: минимальный интервал между обновлениями UI (1 секунда)
            last_update_time = 0.0

            # Callback для обновления прогресса (этап 1: получение данных = 0-50%)
            async def progress_update(value: float):
                nonlocal last_update_time

                # Масштабируем прогресс: 0-100% fetch -> 0-50% общий
                total_progress = value * 0.5

                # Определение текущей фазы
                if value <= 5:
                    phase = "📁 Получение проекта..."
                elif value <= 40:
                    phase = "🔄 Получение задач (рекурсивно)..."
                elif value <= 55:
                    phase = "✅ Получение чеклистов..."
                elif value <= 75:
                    phase = "🔗 Получение связей..."
                elif value <= 90:
                    phase = "💬 Получение комментариев..."
                else:
                    phase = "🔍 Проверка связанных задач..."

                # Throttling: обновляем UI только раз в секунду или при завершении
                current_time = time.time()
                if current_time - last_update_time >= UPDATE_INTERVAL or value >= 100:
                    last_update_time = current_time
                    await manager.update({
                        "is_cloning": True,
                        "progress": int(total_progress),
                        "phase": phase,
                    })

            cloner.set_progress_callback(progress_update)

            # Этап 1: Получение данных
            project_data = await cloner.fetch_project_data(project_id)

            # Callback для клонирования (этап 2: клонирование = 50-100%)
            async def clone_progress_update(value: float):
                nonlocal last_update_time

                # Масштабируем прогресс: 0-100% clone -> 50-100% общий
                total_progress = 50 + value * 0.5

                if value <= 8:
                    phase = "📁 Создание проекта..."
                elif value <= 40:
                    phase = "📋 Клонирование задач..."
                elif value <= 50:
                    phase = "🌳 Восстановление иерархии..."
                elif value <= 65:
                    phase = "✅ Восстановление чеклистов..."
                elif value <= 80:
                    phase = "🔗 Восстановление связей..."
                else:
                    phase = "💬 Восстановление комментариев..."

                # Throttling: обновляем UI только раз в секунду или при завершении
                current_time = time.time()
                if current_time - last_update_time >= UPDATE_INTERVAL or value >= 100:
                    last_update_time = current_time
                    await manager.update({
                        "is_cloning": True,
                        "progress": int(total_progress),
                        "phase": phase,
                    })

            cloner.set_progress_callback(clone_progress_update)

            # Этап 2: Клонирование
            result = await cloner.clone_project(
                project_data=project_data,
                new_project_name=new_name,
                target_queue=queue
            )

            # Завершено - показываем результат
            await manager.update({
                "is_cloning": False,
                "result": result.success,
                "new_project_name": result.new_project_name,
                "new_project_short_id": result.new_project_short_id,
                "created_count": len(result.new_issues_mapping),
                "project_url": f"https://tracker.yandex.ru/pages/projects/{result.new_project_short_id}",
                "error": "\n".join(result.errors) if not result.success else None,
            })

    except Exception as e:
        # Ошибка - показываем сообщение об ошибке
        await manager.update({
            "is_cloning": False,
            "result": False,
            "error": str(e),
        })
