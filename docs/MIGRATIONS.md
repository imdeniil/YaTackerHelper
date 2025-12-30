# Database Migrations с Alembic

Проект использует Alembic для управления миграциями базы данных.

## Структура

```
alembic/
├── versions/           # Файлы миграций
├── env.py             # Конфигурация окружения Alembic
└── script.py.mako     # Шаблон для новых миграций

alembic.ini            # Основной конфигурационный файл
```

## Основные команды

### Применить миграции

```bash
# Применить все непримененные миграции
uv run alembic upgrade head

# Применить конкретную миграцию
uv run alembic upgrade <revision_id>

# Откатить одну миграцию назад
uv run alembic downgrade -1

# Откатить до конкретной ревизии
uv run alembic downgrade <revision_id>
```

### Просмотр истории миграций

```bash
# Показать текущую ревизию
uv run alembic current

# Показать историю миграций
uv run alembic history

# Показать детали конкретной миграции
uv run alembic show <revision_id>
```

### Создание новых миграций

```bash
# Создать пустую миграцию
uv run alembic revision -m "description"

# Создать миграцию с автогенерацией изменений
uv run alembic revision --autogenerate -m "description"
```

## Важные замечания

1. **DATABASE_URL**: Alembic автоматически загружает URL базы данных из переменной окружения `DATABASE_URL` через файл `.env`

2. **Автогенерация**: При использовании `--autogenerate` Alembic сравнивает модели SQLAlchemy с текущей схемой БД и генерирует миграцию автоматически. Всегда проверяйте сгенерированный код!

3. **Резервные копии**: Перед применением миграций на продакшене всегда делайте backup базы данных

4. **Порядок применения**: Миграции применяются в порядке их создания. Alembic отслеживает какие миграции уже применены

## Пример: Применение текущей миграции

Для добавления поля `is_billing_contact`:

```bash
# Проверить текущую ревизию
uv run alembic current

# Применить миграцию
uv run alembic upgrade head

# Проверить что миграция применена
uv run alembic current
```

## Откат миграции

Если что-то пошло не так:

```bash
# Откатить последнюю миграцию
uv run alembic downgrade -1
```

## Troubleshooting

### Ошибка "Can't locate revision identified by"
- Проверьте что DATABASE_URL правильный в .env
- Убедитесь что таблица `alembic_version` существует в БД
- Попробуйте `uv run alembic stamp head` для установки текущей ревизии

### Ошибка при autogenerate
- Убедитесь что все модели импортированы в `alembic/env.py`
- Проверьте что `target_metadata = Base.metadata` указывает на правильный Base

### База данных не в sync с моделями
- Используйте `uv run alembic revision --autogenerate -m "sync models"` для создания синхронизирующей миграции
- Проверьте сгенерированную миграцию перед применением!
