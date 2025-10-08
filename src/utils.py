"""Вспомогательные утилиты для работы с проектами."""

from typing import Dict, Any, List
from aiogram_dialog import DialogManager


async def update_progress_in_dialog(
    manager: DialogManager, progress: float
) -> None:
    """
    Обновить прогресс в aiogram-dialog.

    Args:
        manager: DialogManager из aiogram-dialog
        progress: Значение прогресса (0-100)
    """
    await manager.update({"progress": progress})


def create_progress_callback(manager: DialogManager):
    """
    Создать callback функцию для обновления прогресса.

    Args:
        manager: DialogManager из aiogram-dialog

    Returns:
        Async функция для обновления прогресса
    """

    async def callback(progress: float) -> None:
        await update_progress_in_dialog(manager, progress)

    return callback


def format_project_summary(project_data: Dict[str, Any]) -> str:
    """
    Форматировать краткую информацию о проекте.

    Args:
        project_data: Данные проекта

    Returns:
        Отформатированная строка
    """
    summary = project_data.get("summary", "Без названия")
    issues_count = len(project_data.get("issues", []))
    return f"📁 {summary}\n📋 Задач: {issues_count}"


def format_clone_result(result) -> str:
    """
    Форматировать результат клонирования.

    Args:
        result: CloneResult

    Returns:
        Отформатированная строка
    """
    if result.success:
        return (
            f"✅ Проект успешно склонирован!\n"
            f"🆔 ID: {result.new_project_id}\n"
            f"📋 Создано задач: {len(result.new_issues_mapping)}"
        )
    else:
        errors = "\n".join(result.errors)
        return f"❌ Ошибка клонирования:\n{errors}"


def extract_issue_keys(issues: List[Dict[str, Any]]) -> List[str]:
    """
    Извлечь ключи задач из списка.

    Args:
        issues: Список задач

    Returns:
        Список ключей задач
    """
    return [issue.get("key") for issue in issues if issue.get("key")]
