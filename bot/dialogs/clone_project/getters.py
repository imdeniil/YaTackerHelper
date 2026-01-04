"""Data getters для диалога клонирования проекта"""

from aiogram_dialog import DialogManager
from src.tracker_client import TrackerClient


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
