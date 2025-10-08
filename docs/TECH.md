# Технический стек и архитектура

## Оглавление
- [Технологический стек](#технологический-стек)
- [Архитектурные принципы](#архитектурные-принципы)
- [Правила стилизации кода](#правила-стилизации-кода)

## Технологический стек

### Основные библиотеки

1. **YaTrackerApi** - асинхронный клиент для Yandex Tracker API
   - Документация: `docs/YaTrackerApi.md`
   - Используется для всех операций с Tracker

2. **aiogram** + **aiogram-dialog** - фреймворк для Telegram ботов
   - aiogram-dialog для создания диалогов
   - Виджет Progress для отображения прогресса выполнения
   - FSM (Finite State Machine) для управления состояниями

3. **SQLAlchemy** + **asyncpg** - работа с базой данных
   - SQLAlchemy ORM для моделей (User, UserSettings)
   - asyncpg для асинхронного подключения к PostgreSQL
   - Асинхронные сессии через async_sessionmaker

4. **PostgreSQL** - база данных
   - Хранение пользователей и их настроек
   - Ролевая система (Owner, Manager, Worker)

5. **python-dotenv** - загрузка переменных окружения из .env файла

6. **asyncio** - асинхронное программирование

### Инструменты разработки

- **uv** - менеджер пакетов и публикации
- **Python 3.9+** - минимальная версия Python

## Архитектурные принципы

### 1. Модульность

Проект разделен на независимые модули:
- `tracker_client` - работа с API
- `project_cloner` - бизнес-логика клонирования
- `utils` - вспомогательные функции

### 2. Асинхронность

Все операции с API выполняются асинхронно:
```python
async with TrackerClient() as tracker:
    await tracker.client.issues.get(...)
```

### 3. Context Manager паттерн

Клиент использует async context manager для управления ресурсами:
```python
async with TrackerClient() as tracker:
    # Автоматическое открытие и закрытие соединения
```

### 4. Callback для прогресса

Поддержка как синхронных, так и асинхронных callback функций:
```python
# Синхронный
cloner.set_progress_callback(lambda x: print(x))

# Асинхронный
async def async_callback(progress):
    await manager.update({"progress": progress})

cloner.set_progress_callback(async_callback)
```

### 5. Dataclass для структур данных

Использование dataclass для типизированных структур:
```python
@dataclass
class ProjectData:
    project: Dict[str, Any]
    issues: List[Dict[str, Any]] = field(default_factory=list)
```

### 6. Обработка ошибок

- Try-except блоки для API вызовов
- Сбор ошибок в `CloneResult.errors`
- Продолжение работы при ошибках в чеклистах/связях

## Правила стилизации кода

### 1. Docstrings

Все публичные методы и классы должны иметь docstrings в Google стиле:

```python
def method(arg1: str, arg2: int) -> bool:
    """
    Краткое описание метода.

    Args:
        arg1: Описание первого аргумента
        arg2: Описание второго аргумента

    Returns:
        Описание возвращаемого значения
    """
```

### 2. Type Hints

Обязательное использование type hints для всех параметров и возвращаемых значений:

```python
async def fetch_data(project_id: str) -> ProjectData:
    ...
```

### 3. Именование

- **Классы**: PascalCase (`ProjectCloner`, `TrackerClient`)
- **Функции/методы**: snake_case (`fetch_project_data`, `clone_project`)
- **Константы**: UPPER_CASE (`API_TIMEOUT`, `MAX_RETRIES`)
- **Приватные методы**: начинаются с `_` (`_update_progress`)

### 4. Структура модулей

```python
"""Описание модуля."""

# Стандартные библиотеки
import os
import asyncio

# Сторонние библиотеки
from typing import Optional, Dict
from dotenv import load_dotenv

# Локальные импорты
from .utils import helper_function


class MyClass:
    """Класс делает что-то."""

    def __init__(self):
        """Инициализация."""
        pass
```

### 5. Длина строк

- Максимум 88 символов (Black formatter стандарт)
- Перенос длинных параметров на новые строки

### 6. Комментарии

- Используются для объяснения "почему", а не "что"
- Шаги в сложной логике нумеруются:

```python
# 1. Получить проект (10%)
project = await self.tracker.client.entities.get(...)

# 2. Получить все задачи проекта (30%)
issues = await self._fetch_project_issues(project_id)
```

### 7. Async/Await

- Все методы работающие с I/O - асинхронные
- Использование `await` вместо `.result()` или `asyncio.run()`

## Интеграция с aiogram-dialog

### Динамические окна с Progress виджетом

Используется подход с одним окном и условиями `when` для переключения состояний:

```python
# Handler НЕ делает switch_to - остается на том же окне
async def on_start_clone(callback, button, manager):
    manager.dialog_data["is_cloning"] = True
    manager.dialog_data["progress"] = 0

    bg = manager.bg()
    asyncio.create_task(background_task(bg))

# Фоновая задача обновляет данные через manager.update()
async def background_task(manager: DialogManager):
    cloner.set_progress_callback(lambda v: manager.update({
        "is_cloning": True,
        "progress": int(v)
    }))
    await cloner.fetch_project_data(project_id)

    # Завершение
    await manager.update({
        "is_cloning": False,
        "result": result
    })

# Окно с динамическими состояниями
Window(
    # Подтверждение
    Const("Начать?", when=~F["is_cloning"] & ~F["result"]),
    Button(..., when=~F["is_cloning"] & ~F["result"]),

    # Прогресс
    Progress("progress", 10, when=F["is_cloning"]),

    # Результат
    Format("Готово: {result}", when=~F["is_cloning"] & F["result"]),

    state=MyState.main,  # Одно окно для всех состояний
)
```

**Ключевой принцип:** НЕ переключаться между окнами (`switch_to`), а менять содержимое одного окна через условия `when`.

См. `docs/aiogram_dialog.md` для подробной документации.

## База данных

### Модели SQLAlchemy

Все модели используют асинхронные сессии:

```python
from bot.database import get_session, UserCRUD

async with get_session() as session:
    user = await UserCRUD.get_user_by_telegram_id(session, telegram_id)
```

### Миграции

Используется Alembic для управления миграциями БД.

### Подключение

DATABASE_URL настраивается через .env:
```
DATABASE_URL="postgresql+asyncpg://user:password@host:port/database"
```

## Зависимости

Основные зависимости указаны в `pyproject.toml`:
- YaTrackerApi
- aiogram + aiogram-dialog
- sqlalchemy + asyncpg
- alembic
- python-dotenv

См. `pyproject.toml` для полного списка версий.
