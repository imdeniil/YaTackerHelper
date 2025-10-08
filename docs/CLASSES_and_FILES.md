# Структура классов и файлов проекта

## Оглавление
- [Файловая структура](#файловая-структура)
- [Классы](#классы)
- [Dataclasses](#dataclasses)

## Файловая структура

```
YaTackerHelper/
├── src/
│   ├── __init__.py              # Экспорт основных классов
│   ├── tracker_client.py        # Клиент для работы с YaTrackerApi
│   ├── project_cloner.py        # Основной класс клонирования
│   └── utils.py                 # Вспомогательные утилиты
├── bot/
│   ├── __init__.py
│   ├── config.py                # Конфигурация бота (BotConfig)
│   ├── states.py                # FSM States (MainMenu, CloneProject, ProjectInfo, UserManagement, UserSettings)
│   ├── handlers/
│   │   ├── __init__.py
│   │   └── commands.py          # Обработчики команд (/start, /help, /cancel)
│   ├── dialogs/
│   │   ├── __init__.py
│   │   ├── main_menu.py         # Главное меню
│   │   ├── clone_project.py     # Клонирование проектов (динамическое окно)
│   │   ├── project_info.py      # Информация о проекте
│   │   ├── user_management.py   # Управление пользователями (CRUD)
│   │   └── user_settings.py     # Настройки пользователя
│   ├── middlewares/
│   │   ├── __init__.py
│   │   ├── auth.py              # Middleware авторизации
│   │   └── message_cleanup.py   # Middleware очистки сообщений
│   └── database/
│       ├── __init__.py
│       ├── models.py            # SQLAlchemy модели (User, UserSettings, UserRole)
│       ├── database.py          # Подключение к БД, сессии
│       └── crud.py              # CRUD операции (UserCRUD)
├── examples/
│   ├── simple_usage.py          # Простой пример использования
│   └── aiogram_dialog_integration.py  # Интеграция с aiogram-dialog
├── docs/
│   ├── YaTrackerApi.md          # Документация API
│   ├── YaTrackerQuery.md        # Документация языка запросов
│   ├── aiogram_dialog.md        # Особенности работы с aiogram-dialog
│   ├── DOCKER.md                # Документация по Docker
│   ├── TRANSIT.md               # Текущий контекст проекта
│   ├── CLASSES_and_FILES.md     # Этот файл
│   ├── TECH.md                  # Технический стек
│   └── CHANGELOG.md             # История изменений
├── main.py                      # Точка входа бота (автоматическая инициализация БД)
├── .env                         # Переменные окружения
├── .gitignore                   # Git игнорируемые файлы
└── pyproject.toml               # Конфигурация проекта
```

## Классы

### TrackerClient
**Файл:** `src/tracker_client.py`

Обертка над YandexTrackerClient с автоматической загрузкой credentials из .env файла.

**Методы:**
- `__init__(oauth_token, org_id, log_level)` - инициализация
- `__aenter__()` - вход в async context manager
- `__aexit__()` - выход из async context manager
- `client` (property) - получение экземпляра YandexTrackerClient

**Использование:**
```python
async with TrackerClient() as tracker:
    # Работа с tracker.client
```

### ProjectCloner
**Файл:** `src/project_cloner.py`

Основной класс для клонирования проектов Yandex Tracker.

**Методы:**

#### Публичные
- `__init__(tracker_client)` - инициализация с TrackerClient
- `set_progress_callback(callback)` - установка callback для прогресса
- `fetch_project_data(project_id)` -> ProjectData - получение всех данных проекта
- `clone_project(project_data, new_project_name, target_queue)` -> CloneResult - клонирование

#### Приватные
- `_update_progress(value)` - обновление прогресса (0-100)
- `_fetch_project_issues(project_id)` - получение задач проекта
- `_fetch_all_checklists(issues)` - получение всех чеклистов
- `_fetch_all_links(issues)` - получение всех связей
- `_fetch_all_comments(issues)` - получение всех комментариев
- `_create_project_copy(original_project, new_name)` - создание копии проекта
- `_clone_issues(issues, queue, project_id)` - клонирование задач
- `_restore_checklists(checklists, issues_mapping)` - восстановление чеклистов
- `_restore_links(links, issues_mapping)` - восстановление связей
- `_restore_comments(comments, issues_mapping)` - восстановление комментариев

**Пример использования:**
```python
cloner = ProjectCloner(tracker)
cloner.set_progress_callback(my_callback)
data = await cloner.fetch_project_data("project_id")
result = await cloner.clone_project(data, "Новое имя", "QUEUE")
```

## Dataclasses

### ProjectData
**Файл:** `src/project_cloner.py`

Хранит все данные проекта для клонирования.

**Поля:**
- `project: Dict[str, Any]` - данные проекта
- `issues: List[Dict[str, Any]]` - список задач
- `checklists: Dict[str, List[Dict[str, Any]]]` - чеклисты по задачам
- `links: Dict[str, List[Dict[str, Any]]]` - связи по задачам
- `comments: Dict[str, List[Dict[str, Any]]]` - комментарии по задачам

### CloneResult
**Файл:** `src/project_cloner.py`

Результат операции клонирования.

**Поля:**
- `success: bool` - успешность операции
- `new_project_id: Optional[str]` - ID нового проекта
- `new_issues_mapping: Dict[str, str]` - маппинг старых ключей задач на новые
- `errors: List[str]` - список ошибок

## База данных

### User
**Файл:** `bot/database/models.py`

SQLAlchemy модель пользователя бота.

**Поля:**
- `id: int` - внутренний ID (PK)
- `telegram_id: int` - Telegram ID (unique, indexed)
- `telegram_username: str` - Username в Telegram
- `tracker_login: str` - Логин в Yandex Tracker
- `display_name: str` - ФИО пользователя из Tracker API
- `role: UserRole` - Роль пользователя (owner/manager/worker)
- `created_at: datetime` - Дата создания
- `settings: UserSettings` - Связь 1:1 с настройками

### UserSettings
**Файл:** `bot/database/models.py`

SQLAlchemy модель настроек пользователя.

**Поля:**
- `id: int` - внутренний ID (PK)
- `user_id: int` - FK к User (unique)
- `default_queue: str` - Очередь по умолчанию (default: ZADACIBMT)
- `default_portfolio: str` - Портфель по умолчанию (default: 65cde69d486b9524503455b7)
- `user: User` - Связь с пользователем

### UserRole
**Файл:** `bot/database/models.py`

Enum для ролей пользователей:
- `OWNER` - Владелец (полный доступ)
- `MANAGER` - Менеджер (копирование проектов)
- `WORKER` - Работник (будет добавлено позже)

### UserCRUD
**Файл:** `bot/database/crud.py`

Класс с CRUD операциями для пользователей.

**Методы:**
- `create_user(session, telegram_username, tracker_login, display_name, role, ...)` - создание пользователя
- `get_user_by_telegram_id(session, telegram_id)` - получение по Telegram ID
- `get_user_by_telegram_username(session, telegram_username)` - получение по username
- `get_user_by_id(session, user_id)` - получение по внутреннему ID
- `get_all_users(session)` - получение всех пользователей
- `update_user(session, user_id, **kwargs)` - обновление пользователя (включая display_name)
- `update_user_settings(session, user_id, default_queue, default_portfolio)` - обновление настроек
- `delete_user(session, user_id)` - удаление пользователя

## Middleware

### AuthMiddleware
**Файл:** `bot/middlewares/auth.py`

Middleware для проверки авторизации пользователей.

**Логика:**
1. Извлекает telegram_id из update
2. Проверяет наличие пользователя в БД
3. Если пользователь не найден - блокирует и отправляет ошибку
4. Если найден - добавляет user и user_settings в middleware_data

## Вспомогательные функции

**Файл:** `src/utils.py`

- `update_progress_in_dialog(manager, progress)` - обновление прогресса в DialogManager
- `create_progress_callback(manager)` - создание callback функции для прогресса
- `format_project_summary(project_data)` - форматирование информации о проекте
- `format_clone_result(result)` - форматирование результата клонирования
- `extract_issue_keys(issues)` - извлечение ключей задач из списка
