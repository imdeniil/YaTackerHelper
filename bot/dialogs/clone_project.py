"""Диалог для клонирования проекта."""

import asyncio
import time
from operator import itemgetter
from aiogram import F
from aiogram.types import Message, CallbackQuery
from aiogram_dialog import Dialog, Window, DialogManager, ShowMode
from aiogram_dialog.widgets.kbd import Button, Back, Cancel, Select, ScrollingGroup, Url
from aiogram_dialog.widgets.text import Const, Format, Progress
from aiogram_dialog.widgets.input import MessageInput

from bot.states import CloneProject
from src.tracker_client import TrackerClient
from src.project_cloner import ProjectCloner


# ========== GETTERS ==========


async def get_select_project_data(dialog_manager: DialogManager, **kwargs):
    """Getter для окна выбора проекта с загрузкой списка (с кэшированием)."""
    # Проверяем кэш - если проекты уже загружены, не делаем повторный запрос
    if "template_projects" in dialog_manager.dialog_data:
        projects = dialog_manager.dialog_data["template_projects"]
    else:
        # Загружаем проекты со словом "шаблон"
        try:
            async with TrackerClient() as tracker:
                # Получаем все проекты с полем summary
                projects_raw = await tracker.client.entities.search(
                    entity_type="project",
                    fields="summary,id"
                )

                # Если dict - это пагинированный ответ, берем values
                if isinstance(projects_raw, dict):
                    pages = projects_raw.get("pages", 1)

                    # Если страниц больше 1 - загружаем все за один запрос
                    if isinstance(pages, int) and pages > 1:
                        per_page = pages * 50
                        projects_raw = await tracker.client.entities.search(
                            entity_type="project",
                            fields="summary,id",
                            per_page=per_page
                        )

                    if "values" in projects_raw:
                        projects_raw = projects_raw["values"]
                    else:
                        projects_raw = []

                # Если пустой список - пробуем без fields
                if not projects_raw:
                    projects_raw = await tracker.client.entities.search(
                        entity_type="project"
                    )
                    # Снова проверяем на dict
                    if isinstance(projects_raw, dict):
                        pages = projects_raw.get("pages", 1)
                        # Если страниц больше 1 - загружаем все
                        if isinstance(pages, int) and pages > 1:
                            per_page = pages * 50
                            projects_raw = await tracker.client.entities.search(
                                entity_type="project",
                                per_page=per_page
                            )

                        if "values" in projects_raw:
                            projects_raw = projects_raw["values"]

                # Фильтруем локально по слову "шаблон" в названии
                projects = []
                for proj in projects_raw:
                    if not isinstance(proj, dict):
                        continue

                    proj_id = proj.get("id", "")
                    if not proj_id:
                        continue

                    # Проверяем где находится summary
                    summary = proj.get("fields", {}).get("summary", "")
                    if not summary:
                        summary = proj.get("summary", "")

                    if not summary:
                        summary = f"Проект #{proj.get('shortId', 'N/A')}"

                    # Фильтруем по слову "шаблон"
                    if "шаблон" in summary.lower():
                        projects.append((summary, proj_id))

                # Сохраняем для повторного использования
                dialog_manager.dialog_data["template_projects"] = projects
        except Exception as e:
            projects = []
            dialog_manager.dialog_data["error"] = f"Ошибка загрузки проектов: {str(e)}"

    return {
        "projects": projects,
        "count": len(projects)
    }


async def get_confirm_data(dialog_manager: DialogManager, **kwargs):
    """Getter для окна подтверждения проекта."""
    project_id = dialog_manager.dialog_data.get("project_id", "Не указан")
    project_name = dialog_manager.dialog_data.get("project_name", "Неизвестен")
    return {
        "project_id": project_id,
        "project_name": project_name
    }


async def get_new_name_data(dialog_manager: DialogManager, **kwargs):
    """Getter для окна ввода имени."""
    project_id = dialog_manager.dialog_data.get("project_id", "")
    project_name = dialog_manager.dialog_data.get("project_name", "Неизвестен")
    return {
        "project_id": project_id,
        "project_name": project_name
    }


async def get_queue_data(dialog_manager: DialogManager, **kwargs):
    """Getter для окна ввода очереди (с кэшированием для пагинации)."""
    new_name = dialog_manager.dialog_data.get("new_name", "Без названия")
    user_settings = kwargs.get("user_settings")

    # Проверяем есть ли дефолтная очередь
    default_queue = user_settings.default_queue if user_settings else None

    # Определяем режим отображения
    queue_step = dialog_manager.dialog_data.get("queue_step", "")

    # Загружаем список очередей если нужно (с кэшированием)
    queues = []
    if queue_step == "select_queue_list" or not default_queue:
        # Проверяем кэш
        if "cached_queues" in dialog_manager.dialog_data:
            queues = dialog_manager.dialog_data["cached_queues"]
        else:
            # Загружаем и кэшируем очереди
            try:
                async with TrackerClient() as tracker:
                    queues_raw = await tracker.client.queues.get()
                    queues = [
                        {"key": q.get("key", ""), "name": q.get("name", q.get("key", ""))}
                        for q in queues_raw
                    ]
                    # Сохраняем в кэш
                    dialog_manager.dialog_data["cached_queues"] = queues
            except Exception as e:
                dialog_manager.dialog_data["error"] = f"Ошибка загрузки очередей: {str(e)}"

    return {
        "new_name": new_name,
        "default_queue": default_queue,
        "has_default": bool(default_queue),
        "queue_step": queue_step,
        "queues": queues,
    }


async def get_final_confirm_data(dialog_manager: DialogManager, **kwargs):
    """Getter для финального подтверждения/прогресса/результата (динамическое окно)."""
    is_cloning = dialog_manager.dialog_data.get("is_cloning", False)
    progress = dialog_manager.dialog_data.get("progress", 0)

    return {
        # Данные подтверждения
        "project_id": dialog_manager.dialog_data.get("project_id", ""),
        "project_name": dialog_manager.dialog_data.get("project_name", "Неизвестен"),
        "new_name": dialog_manager.dialog_data.get("new_name", ""),
        "queue": dialog_manager.dialog_data.get("queue", ""),

        # Данные прогресса
        "is_cloning": is_cloning,
        "progress": progress,
        "phase": dialog_manager.dialog_data.get("phase", "Инициализация..."),

        # Данные результата
        "result": dialog_manager.dialog_data.get("result"),
        "new_project_name": dialog_manager.dialog_data.get("new_project_name", ""),
        "new_project_short_id": dialog_manager.dialog_data.get("new_project_short_id", ""),
        "created_count": dialog_manager.dialog_data.get("created_count", 0),
        "project_url": dialog_manager.dialog_data.get("project_url", ""),
        "error": dialog_manager.dialog_data.get("error"),
    }


# ========== HANDLERS ==========


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
            UPDATE_INTERVAL = 1.0

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


# ========== DIALOG ==========


clone_project_dialog = Dialog(
    # Окно 1: Выбор проекта
    Window(
        Const("Выберите проект для клонирования:", when="count"),
        Const("❌ Не найдено проектов со словом 'шаблон'", when=lambda data, widget, manager: not data.get("count")),
        ScrollingGroup(
            Select(
                Format("{item[0]}"),  # Отображаем название проекта
                id="project_select",
                item_id_getter=itemgetter(1),  # ID проекта берем из второго элемента кортежа
                items="projects",
                on_click=on_project_selected,
            ),
            id="projects_scroll",
            width=1,
            height=5,
            when="count",  # Показываем только если есть проекты
        ),
        Cancel(Const("❌ Отмена")),
        state=CloneProject.select_project,
        getter=get_select_project_data,
    ),
    # Окно 2: Подтверждение проекта
    Window(
        Format("📁 Проект: <b>{project_name}</b>\n"),
        Button(
            Const("✅ Продолжить"),
            id="confirm_project",
            on_click=on_confirm_project,
        ),
        Back(Const("◀️ Назад")),
        state=CloneProject.confirm_project,
        getter=get_confirm_data,
    ),
    # Окно 3: Ввод имени нового проекта
    Window(
        Format("Клонируется проект: <b>{project_name}</b>\n"),
        Const("Введите название для нового проекта:"),
        MessageInput(on_new_name_input),
        Back(Const("◀️ Назад")),
        state=CloneProject.enter_new_name,
        getter=get_new_name_data,
    ),
    # Окно 4: Выбор целевой очереди
    Window(
        Format("Новый проект: <b>{new_name}</b>\n"),
        # Если есть дефолтная очередь и не в режиме выбора из списка
        Format(
            "Очередь из настроек: <code>{default_queue}</code>\n\n"
            "Использовать эту очередь или выбрать другую?",
            when=lambda data, widget, manager: data.get("has_default") and data.get("queue_step") == "",
        ),
        Button(
            Const("✅ Использовать"),
            id="use_default_queue",
            on_click=on_use_default_queue,
            when=lambda data, widget, manager: data.get("has_default") and data.get("queue_step") == "",
        ),
        Button(
            Const("📋 Выбрать другую"),
            id="enter_custom_queue",
            on_click=on_enter_custom_queue,
            when=lambda data, widget, manager: data.get("has_default") and data.get("queue_step") == "",
        ),
        # Выбор из списка (если нет дефолта или выбран режим выбора из списка)
        Const(
            "Выберите очередь из списка:",
            when=lambda data, widget, manager: not data.get("has_default") or data.get("queue_step") == "select_queue_list",
        ),
        ScrollingGroup(
            Select(
                Format("{item[name]} ({item[key]})"),
                id="clone_queue_select",
                item_id_getter=lambda x: x["key"],
                items="queues",
                on_click=on_clone_queue_selected,
            ),
            id="clone_queues_scroll",
            width=1,
            height=5,
            when=lambda data, widget, manager: not data.get("has_default") or data.get("queue_step") == "select_queue_list",
        ),
        Back(Const("◀️ Назад")),
        state=CloneProject.enter_queue,
        getter=get_queue_data,
    ),
    # Окно 5: Динамическое окно (подтверждение/прогресс/результат)
    Window(
        # === СОСТОЯНИЕ 1: Подтверждение (is_cloning=False, result=None) ===
        Format("📁 Исходный проект: <b>{project_name}</b>", when=~F["is_cloning"] & ~F["result"]),
        Format("📝 Новый проект: <b>{new_name}</b>", when=~F["is_cloning"] & ~F["result"]),
        Format("📮 Очередь: <b>{queue}</b>\n", when=~F["is_cloning"] & ~F["result"]),
        Const("⚠️ Начать клонирование?", when=~F["is_cloning"] & ~F["result"]),
        Button(
            Const("🚀 Начать"),
            id="start_clone",
            on_click=on_start_clone,
            when=~F["is_cloning"] & ~F["result"]
        ),
        Back(Const("◀️ Назад"), when=~F["is_cloning"] & ~F["result"]),

        # === СОСТОЯНИЕ 2: Клонирование (is_cloning=True) ===
        Format("\n{phase}\n", when=F["is_cloning"]),
        Progress("progress", 10, when=F["is_cloning"]),

        # === СОСТОЯНИЕ 3: Результат (is_cloning=False, result есть) ===
        # Успех
        Format("📁 Проект: <b>{new_project_name}</b>", when=~F["is_cloning"] & F["result"]),
        Format("📋 Создано задач: <b>{created_count}</b>\n", when=~F["is_cloning"] & F["result"]),
        Url(
            Const("🔗 Открыть проект"),
            Format("{project_url}"),
            when=~F["is_cloning"] & F["result"]
        ),
        Cancel(Const("🏠 Главное меню"), when=~F["is_cloning"] & F["result"]),

        # Ошибка
        Const("❌ <b>Ошибка клонирования</b>\n", when=~F["is_cloning"] & ~F["result"] & F["error"]),
        Format("⚠️ {error}\n", when=~F["is_cloning"] & ~F["result"] & F["error"]),
        Const("💡 Проверьте права доступа и повторите попытку.", when=~F["is_cloning"] & ~F["result"] & F["error"]),
        Cancel(Const("🏠 Главное меню"), when=~F["is_cloning"] & ~F["result"] & F["error"]),

        # Предотвращаем сброс во время выполнения
        MessageInput(on_message_during_clone),

        state=CloneProject.confirm_clone,
        getter=get_final_confirm_data,
    ),
)
