"""Модуль для копирования проектов из Yandex Tracker."""

import asyncio
from typing import Optional, Callable, Dict, List, Any
from dataclasses import dataclass, field
from YaTrackerApi import YandexTrackerClient

@dataclass
class ProjectData:
    """Данные проекта для клонирования."""

    project: Dict[str, Any]
    issues: List[Dict[str, Any]] = field(default_factory=list)
    checklists: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)
    links: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)
    comments: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)
    parent_child: Dict[str, str] = field(default_factory=dict)  # {child_key: parent_key}

@dataclass
class CloneResult:
    """Результат клонирования проекта."""

    success: bool
    new_project_id: Optional[str] = None
    new_project_short_id: Optional[int] = None
    new_project_name: Optional[str] = None
    new_issues_mapping: Dict[str, str] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)


class ProjectCloner:
    """Класс для клонирования проектов Yandex Tracker с поддержкой прогресса."""

    def __init__(self, tracker_client: YandexTrackerClient):
        """
        Инициализация клонера проектов.

        Args:
            tracker_client: Экземпляр TrackerClient
        """
        self.tracker = tracker_client
        self._progress_callback: Optional[Callable[[float], None]] = None

    def set_progress_callback(self, callback: Callable[[float], None]) -> None:
        """
        Установить callback для обновления прогресса.

        Args:
            callback: Функция принимающая значение прогресса (0-100)
        """
        self._progress_callback = callback

    async def _update_progress(self, value: float) -> None:
        """
        Обновить прогресс выполнения.

        Args:
            value: Значение прогресса (0-100)
        """
        if self._progress_callback:
            if asyncio.iscoroutinefunction(self._progress_callback):
                await self._progress_callback(value)
            else:
                self._progress_callback(value)

    async def fetch_project_data(self, project_id: str) -> ProjectData:
        """
        Получить все данные проекта с рекурсивным обходом подзадач.

        Args:
            project_id: ID проекта

        Returns:
            ProjectData с полными данными проекта
        """
        await self._update_progress(0)

        # 1. Получить проект со всеми полями (5%)
        project = await self.tracker.client.entities.get(
            entity_id=project_id,
            entity_type="project",
            fields="summary,description,lead,teamUsers,teamAccess,parentEntity"
        )
        await self._update_progress(5)

        # 2. Получить все задачи проекта рекурсивно (35%)
        issues, parent_child = await self._fetch_project_issues_recursive(project_id)
        await self._update_progress(40)

        # 3. Получить чеклисты для всех задач (15%)
        checklists = await self._fetch_all_checklists(issues)
        await self._update_progress(55)

        # 4. Получить связи для всех задач (20%)
        links = await self._fetch_all_links(issues)
        await self._update_progress(75)

        # 5. Получить комментарии для всех задач (15%)
        comments = await self._fetch_all_comments(issues)
        await self._update_progress(90)

        # 6. Проверить и дополнить недостающие связанные задачи (10%)
        await self._ensure_all_linked_issues(issues, links, parent_child)
        await self._update_progress(100)

        return ProjectData(
            project=project,
            issues=issues,
            checklists=checklists,
            links=links,
            comments=comments,
            parent_child=parent_child
        )

    async def _fetch_project_issues_recursive(
        self, project_id: str
    ) -> tuple[List[Dict[str, Any]], Dict[str, str]]:
        """
        Получить все задачи проекта включая подзадачи.

        Args:
            project_id: ID проекта

        Returns:
            Кортеж (список всех задач, словарь parent_child связей)
        """
        # Получить ВСЕ задачи проекта за один запрос
        all_issues_raw = await self.tracker.client.issues.search(
            filter={"project": project_id},
            expand=["transitions", "attachments"]
        )

        # Дедупликация по ключу задачи
        seen_keys = set()
        all_issues = []
        parent_child = {}

        for issue in all_issues_raw:
            issue_key = issue.get("key")

            # Пропускаем дубликаты
            if issue_key in seen_keys:
                continue

            seen_keys.add(issue_key)
            all_issues.append(issue)

            # Построить parent_child маппинг
            parent = issue.get("parent")
            if parent and isinstance(parent, dict):
                parent_key = parent.get("key")
                if parent_key:
                    parent_child[issue_key] = parent_key

        return all_issues, parent_child

    async def _ensure_all_linked_issues(
        self,
        issues: List[Dict[str, Any]],
        links: Dict[str, List[Dict[str, Any]]],
        parent_child: Dict[str, str]
    ) -> None:
        """
        Проверить что все связанные задачи включены в список.
        Добавить недостающие если они есть.

        Args:
            issues: Список задач
            links: Словарь связей
            parent_child: Словарь parent-child связей
        """
        issue_keys = {issue.get("key") for issue in issues}

        for issue_key, link_list in links.items():
            for link in link_list:
                linked_key = link.get("object", {}).get("key")

                # Если связанная задача отсутствует - попробовать добавить
                if linked_key and linked_key not in issue_keys:
                    try:
                        linked_issue = await self.tracker.client.issues.get(linked_key)
                        issues.append(linked_issue)
                        issue_keys.add(linked_key)

                        # Проверить parent связь
                        parent_key = linked_issue.get("parent", {}).get("key")
                        if parent_key:
                            parent_child[linked_key] = parent_key
                    except Exception:
                        pass  # Пропускаем недоступные задачи

    async def _fetch_all_checklists(
        self, issues: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Получить чеклисты для всех задач.

        Args:
            issues: Список задач

        Returns:
            Словарь {issue_key: [checklist_items]}
        """
        checklists = {}
        total = len(issues)

        for idx, issue in enumerate(issues):
            issue_key = issue.get("key")
            try:
                checklist_items = await self.tracker.client.issues.checklists.get(
                    issue_id=issue_key
                )
                checklists[issue_key] = checklist_items
            except Exception as e:
                # Если чеклиста нет - продолжаем
                checklists[issue_key] = []

            # Промежуточное обновление прогресса
            if total > 0:
                progress = 40 + (idx + 1) / total * 20
                await self._update_progress(progress)

        return checklists

    async def _fetch_all_links(
        self, issues: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Получить связи для всех задач.

        Args:
            issues: Список задач

        Returns:
            Словарь {issue_key: [links]}
        """
        links = {}
        total = len(issues)

        for idx, issue in enumerate(issues):
            issue_key = issue.get("key")
            try:
                issue_links = await self.tracker.client.issues.links.get(
                    issue_id=issue_key
                )
                links[issue_key] = issue_links
            except Exception:
                links[issue_key] = []

            # Промежуточное обновление прогресса
            if total > 0:
                progress = 60 + (idx + 1) / total * 20
                await self._update_progress(progress)

        return links

    async def _fetch_all_comments(
        self, issues: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Получить комментарии для всех задач.

        Args:
            issues: Список задач

        Returns:
            Словарь {issue_key: [comments]}
        """
        comments = {}
        total = len(issues)

        for idx, issue in enumerate(issues):
            issue_key = issue.get("key")
            try:
                issue_comments = await self.tracker.client.issues.comments.get(
                    issue_id=issue_key
                )
                comments[issue_key] = issue_comments
            except Exception:
                comments[issue_key] = []

            # Промежуточное обновление прогресса
            if total > 0:
                progress = 80 + (idx + 1) / total * 20
                await self._update_progress(progress)

        return comments

    async def clone_project(
        self,
        project_data: ProjectData,
        new_project_name: str,
        target_queue: str
    ) -> CloneResult:
        """
        Создать копию проекта со всеми данными включая иерархию подзадач.

        Args:
            project_data: Данные исходного проекта
            new_project_name: Название нового проекта
            target_queue: Очередь для новых задач

        Returns:
            CloneResult с результатами клонирования
        """
        result = CloneResult(success=False)
        await self._update_progress(0)

        try:
            # 1. Создать новый проект (8%)
            new_project = await self._create_project_copy(
                project_data.project, new_project_name
            )
            result.new_project_id = new_project.get("id")
            result.new_project_short_id = new_project.get("shortId")
            result.new_project_name = new_project_name
            new_project_short_id = new_project.get("shortId")
            await self._update_progress(8)

            # 2. Создать копии всех задач (32%)
            issues_mapping = await self._clone_issues(
                project_data.issues, target_queue, new_project_short_id
            )
            result.new_issues_mapping = issues_mapping
            await self._update_progress(40)

            # 3. Восстановить parent-child связи (10%)
            await self._restore_parent_child(project_data.parent_child, issues_mapping)
            await self._update_progress(50)

            # 4. Восстановить чеклисты (15%)
            await self._restore_checklists(project_data.checklists, issues_mapping)
            await self._update_progress(65)

            # 5. Восстановить связи между задачами (15%)
            await self._restore_links(project_data.links, issues_mapping)
            await self._update_progress(80)

            # 6. Восстановить комментарии (20%)
            await self._restore_comments(project_data.comments, issues_mapping)
            await self._update_progress(100)

            result.success = True

        except Exception as e:
            result.errors.append(str(e))
            result.success = False

        return result

    async def _create_project_copy(
        self, original_project: Dict[str, Any], new_name: str
    ) -> Dict[str, Any]:
        """Создать копию проекта."""
        project_data = {
            "summary": new_name,
            "entity_type": "project",
        }

        # Копируем описание - проверяем несколько возможных мест
        description = None

        # Вариант 1: в корне объекта
        if "description" in original_project and original_project["description"]:
            description = original_project["description"]

        # Вариант 2: в fields.description
        elif "fields" in original_project:
            fields = original_project["fields"]
            if isinstance(fields, dict) and "description" in fields:
                description = fields["description"]

        # Вариант 3: в checkDescription (иногда API возвращает так)
        elif "checkDescription" in original_project:
            description = original_project["checkDescription"]

        if description:
            # Убираем пустые строки
            description = description.strip() if isinstance(description, str) else description
            if description:
                project_data["description"] = description

        # Копируем руководителя
        lead = original_project.get("lead")
        if not lead and "fields" in original_project:
            lead = original_project["fields"].get("lead")

        if lead:
            # Извлекаем id (поля login нет в API!)
            if isinstance(lead, dict):
                project_data["lead"] = lead.get("id")
            else:
                project_data["lead"] = lead

        # Копируем teamAccess
        team_access = original_project.get("teamAccess")
        if team_access is None and "fields" in original_project:
            team_access = original_project["fields"].get("teamAccess")
        if team_access is not None:
            project_data["team_access"] = team_access  # create() принимает team_access (с версии 2.1.3)

        # Копируем участников (если есть)
        team_users = original_project.get("teamUsers")
        if not team_users and "fields" in original_project:
            team_users = original_project["fields"].get("teamUsers")

        if team_users:
            # Извлекаем ID пользователей (поля login нет в API!)
            user_ids = []
            for user in team_users:
                if isinstance(user, dict):
                    user_id = user.get("id")
                    if user_id:
                        user_ids.append(user_id)
                else:
                    user_ids.append(user)
            if user_ids:
                project_data["team_users"] = user_ids  # snake_case для API!

        # Копируем родительский портфель (если есть)
        # API требует формат: {"primary": "parent_id", "secondary": []}
        parent = original_project.get("parentEntity")
        if not parent and "fields" in original_project:
            parent = original_project["fields"].get("parentEntity")

        if parent:
            # ParentEntity из API имеет структуру: {"primary": {"id": "..."}, "secondary": []}
            if isinstance(parent, dict):
                parent_id = None
                secondary_ids = []

                # Проверяем структуру с primary/secondary
                if "primary" in parent:
                    primary = parent.get("primary")
                    if isinstance(primary, dict):
                        parent_id = primary.get("id")
                # Или простая структура с id
                elif parent.get("id"):
                    parent_id = parent.get("id")

                if "secondary" in parent:
                    secondary = parent.get("secondary", [])
                    if isinstance(secondary, list):
                        secondary_ids = secondary

                if parent_id:
                    # API create() требует формат словаря!
                    project_data["parent_entity"] = {
                        "primary": parent_id,
                        "secondary": secondary_ids
                    }
            else:
                # Если parent - это просто строка ID
                project_data["parent_entity"] = {
                    "primary": parent,
                    "secondary": []
                }

        # Создаем проект (с версии 2.1.3 team_access поддерживается в create())
        return await self.tracker.client.entities.create(**project_data)

    async def _clone_issues(
        self, issues: List[Dict[str, Any]], queue: str, project_short_id: int
    ) -> Dict[str, str]:
        """Создать копии всех задач."""
        mapping = {}
        total = len(issues)

        for idx, issue in enumerate(issues):
            old_key = issue.get("key")

            # Подготовить данные для новой задачи
            new_issue_data = {
                "summary": issue.get("summary"),
                "queue": queue,
                "description": issue.get("description", ""),
            }

            # Добавить связь с проектом (используем shortId в формате v3 API)
            if project_short_id:
                new_issue_data["project"] = {"primary": project_short_id}

            # Копировать тип (извлекаем только ключи)
            if "type" in issue:
                issue_type = issue["type"]
                if isinstance(issue_type, dict):
                    new_issue_data["type"] = issue_type.get("key") or issue_type.get("id")
                else:
                    new_issue_data["type"] = issue_type

            # Копировать приоритет
            if "priority" in issue:
                issue_priority = issue["priority"]
                if isinstance(issue_priority, dict):
                    new_issue_data["priority"] = issue_priority.get("key") or issue_priority.get("id")
                else:
                    new_issue_data["priority"] = issue_priority

            # Копировать исполнителя
            if "assignee" in issue:
                assignee = issue["assignee"]
                if isinstance(assignee, dict):
                    new_issue_data["assignee"] = assignee.get("login") or assignee.get("id")
                else:
                    new_issue_data["assignee"] = assignee

            # Копировать теги
            if "tags" in issue and issue["tags"]:
                new_issue_data["tags"] = issue["tags"]

            # Копировать дедлайн
            if "deadline" in issue:
                new_issue_data["deadline"] = issue["deadline"]

            # Копировать время оценки
            if "estimation" in issue:
                new_issue_data["estimation"] = issue["estimation"]

            # Создать задачу
            try:
                new_issue = await self.tracker.client.issues.create(**new_issue_data)
                new_key = new_issue.get("key")
                mapping[old_key] = new_key

                # Добавить наблюдателей после создания задачи
                if "followers" in issue and issue["followers"]:
                    try:
                        followers = issue["followers"]
                        # Извлекаем логины наблюдателей
                        follower_ids = []
                        for follower in followers:
                            if isinstance(follower, dict):
                                follower_id = follower.get("login") or follower.get("id")
                                if follower_id:
                                    follower_ids.append(follower_id)
                            else:
                                follower_ids.append(follower)

                        if follower_ids:
                            await self.tracker.client.issues.update(
                                issue_id=new_key,
                                followers={"add": follower_ids}
                            )
                    except Exception:
                        pass  # Игнорируем ошибки с наблюдателями

            except Exception as e:
                # Логируем ошибку но продолжаем
                pass

            # Обновить прогресс
            if total > 0:
                progress = 10 + (idx + 1) / total * 40
                await self._update_progress(progress)

        return mapping

    async def _restore_parent_child(
        self, parent_child: Dict[str, str], issues_mapping: Dict[str, str]
    ) -> None:
        """
        Восстановить parent-child связи между задачами.

        Args:
            parent_child: Словарь {child_key: parent_key} из исходного проекта
            issues_mapping: Маппинг старых ключей задач на новые
        """
        total = len(parent_child)
        processed = 0

        for old_child_key, old_parent_key in parent_child.items():
            new_child_key = issues_mapping.get(old_child_key)
            new_parent_key = issues_mapping.get(old_parent_key)

            if new_child_key and new_parent_key:
                try:
                    # Обновить задачу, установив parent
                    await self.tracker.client.issues.update(
                        issue_id=new_child_key,
                        parent=new_parent_key
                    )
                except Exception as e:
                    # Логируем ошибку но продолжаем
                    pass

            processed += 1
            if total > 0:
                progress = 40 + processed / total * 10
                await self._update_progress(progress)

    async def _restore_checklists(
        self, checklists: Dict[str, List], issues_mapping: Dict[str, str]
    ) -> None:
        """Восстановить чеклисты в новых задачах."""
        total_items = sum(len(items) for items in checklists.values())
        processed = 0

        for old_key, items in checklists.items():
            new_key = issues_mapping.get(old_key)
            if not new_key:
                continue

            for item in items:
                try:
                    await self.tracker.client.issues.checklists.create(
                        issue_id=new_key,
                        text=item.get("text"),
                        checked=item.get("checked", False),
                    )
                except Exception:
                    pass  # Пропускаем ошибки

                processed += 1
                if total_items > 0:
                    progress = 50 + processed / total_items * 15
                    await self._update_progress(progress)

    async def _restore_links(
        self, links: Dict[str, List], issues_mapping: Dict[str, str]
    ) -> None:
        """Восстановить связи между задачами."""
        total_links = sum(len(link_list) for link_list in links.values())
        processed = 0

        for old_key, link_list in links.items():
            new_key = issues_mapping.get(old_key)
            if not new_key:
                continue

            for link in link_list:
                # Получить связанную задачу
                linked_issue_key = link.get("object", {}).get("key")
                new_linked_key = issues_mapping.get(linked_issue_key)

                if not new_linked_key:
                    continue

                try:
                    await self.tracker.client.issues.links.create(
                        issue_id=new_key,
                        relationship=link.get("type", {}).get("id", "relates"),
                        issue=new_linked_key,
                    )
                except Exception:
                    pass  # Пропускаем ошибки дублирования

                processed += 1
                if total_links > 0:
                    progress = 65 + processed / total_links * 15
                    await self._update_progress(progress)

    async def _restore_comments(
        self, comments: Dict[str, List], issues_mapping: Dict[str, str]
    ) -> None:
        """Восстановить комментарии в новых задачах."""
        total_comments = sum(len(comment_list) for comment_list in comments.values())
        processed = 0

        for old_key, comment_list in comments.items():
            new_key = issues_mapping.get(old_key)
            if not new_key:
                continue

            for comment in comment_list:
                try:
                    await self.tracker.client.issues.comments.create(
                        issue_id=new_key,
                        text=comment.get("text", ""),
                    )
                except Exception:
                    pass  # Пропускаем ошибки

                processed += 1
                if total_comments > 0:
                    progress = 80 + processed / total_comments * 20
                    await self._update_progress(progress)
