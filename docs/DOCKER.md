# Docker развертывание YaTackerHelper

## Содержание

- [Быстрый старт](#быстрый-старт) — запуск с встроенным PostgreSQL
- [Подключение к существующей БД](#подключение-к-существующей-бд) — использование внешней PostgreSQL
- [Управление](#управление)
- [Логи](#логи)
- [Резервное копирование БД](#резервное-копирование-бд)
- [Отладка](#отладка)
- [Архитектура](#архитектура)
- [Производственное развертывание](#производственное-развертывание)
- [Troubleshooting](#troubleshooting)

## Быстрый старт

> 💡 Этот вариант создает и запускает PostgreSQL контейнер вместе с ботом

### 1. Подготовка окружения

```bash
# Клонируй репозиторий (если еще не сделал)
git clone <repository-url>
cd YaTackerHelper

# Скопируй example в .env
cp .env.example .env
```

### 2. Настройка .env

Отредактируй файл `.env`:

```env
# Yandex Tracker API (обязательно)
TRACKER_API_KEY=y0_AgAAAAABhZKPAAzFzwAAAAEsample_token_here
TRACKER_ORG_ID=674252

# Telegram Bot (обязательно)
BOT_TOKEN=7498622514:AAH_sample_bot_token_here

# Database - для Docker используй это значение
DATABASE_URL=postgresql+asyncpg://yatrackerhelper:changeme@postgres:5432/yatrackerhelper

# Пароль для PostgreSQL (опционально)
DB_PASSWORD=your_secure_password_here

# Владелец 1 (обязательно)
OWNER1_USERNAME=iVars_b
OWNER1_TRACKER_LOGIN=concept-rp
OWNER1_DISPLAY_NAME=Айварс Балиньш

# Владелец 2 (опционально)
OWNER2_USERNAME=imdeniil
OWNER2_TRACKER_LOGIN=imdeniil
OWNER2_DISPLAY_NAME=Даниил Павлючик
```

### 3. Запуск

```bash
# Сборка и запуск в фоне
docker-compose up -d --build

# Проверка статуса
docker-compose ps

# Просмотр логов бота
docker-compose logs -f bot

# Просмотр логов БД
docker-compose logs -f postgres
```

## Подключение к существующей БД

> 💡 Этот вариант запускает только бот, подключаясь к уже существующей PostgreSQL БД

### 1. Подготовка окружения

```bash
# Клонируй репозиторий (если еще не сделал)
git clone <repository-url>
cd YaTackerHelper

# Скопируй example в .env
cp .env.example .env
```

### 2. Настройка .env

Отредактируй файл `.env`, настроив подключение к твоей существующей БД:

```env
# Yandex Tracker API (обязательно)
TRACKER_API_KEY=y0_AgAAAAABhZKPAAzFzwAAAAEsample_token_here
TRACKER_ORG_ID=674252

# Telegram Bot (обязательно)
BOT_TOKEN=7498622514:AAH_sample_bot_token_here

# Database - укажи параметры подключения к существующей БД
DATABASE_URL=postgresql+asyncpg://your_user:your_password@your_host:5432/your_database

# Владелец 1 (обязательно)
OWNER1_USERNAME=iVars_b
OWNER1_TRACKER_LOGIN=concept-rp
OWNER1_DISPLAY_NAME=Айварс Балиньш

# Владелец 2 (опционально)
OWNER2_USERNAME=imdeniil
OWNER2_TRACKER_LOGIN=imdeniil
OWNER2_DISPLAY_NAME=Даниил Павлючик
```

### 3. Примеры DATABASE_URL для разных сценариев

#### PostgreSQL на локальной машине (та же машина, где Docker)

**Windows/Mac:**
```env
DATABASE_URL=postgresql+asyncpg://user:password@host.docker.internal:5432/dbname
```

**Linux:**
```env
DATABASE_URL=postgresql+asyncpg://user:password@172.17.0.1:5432/dbname
```

Или добавь `network_mode: "host"` в `docker-compose.bot-only.yml`:
```env
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/dbname
```

#### PostgreSQL на удаленном сервере

```env
DATABASE_URL=postgresql+asyncpg://user:password@192.168.1.100:5432/dbname
# или
DATABASE_URL=postgresql+asyncpg://user:password@db.example.com:5432/dbname
```

### 4. Запуск

```bash
# Сборка и запуск только бота в фоне
docker-compose -f docker-compose.bot-only.yml up -d --build

# Проверка статуса
docker-compose -f docker-compose.bot-only.yml ps

# Просмотр логов
docker-compose -f docker-compose.bot-only.yml logs -f bot
```

### 5. Остановка

```bash
# Остановить контейнер
docker-compose -f docker-compose.bot-only.yml stop

# Остановить и удалить контейнер
docker-compose -f docker-compose.bot-only.yml down
```

### Важные замечания

1. **БД должна существовать**: Бот не создаст БД автоматически, только таблицы внутри нее
2. **PostgreSQL версия**: Рекомендуется PostgreSQL 12+
3. **Права доступа**: Пользователь БД должен иметь права на создание таблиц
4. **Firewall**: Убедись, что PostgreSQL доступна с Docker контейнера
5. **SSL**: Если требуется SSL, добавь `?ssl=require` в конец DATABASE_URL

## Управление

> 💡 **Примечание**: Команды ниже для `docker-compose.yml` (с PostgreSQL).
> Для `docker-compose.bot-only.yml` добавь `-f docker-compose.bot-only.yml` к каждой команде.

### Остановка

```bash
# Остановить контейнеры
docker-compose stop

# Остановить и удалить контейнеры (данные БД сохранятся)
docker-compose down

# Остановить и удалить контейнеры + данные БД (только для docker-compose.yml)
docker-compose down -v
```

**Для bot-only:**
```bash
docker-compose -f docker-compose.bot-only.yml stop
docker-compose -f docker-compose.bot-only.yml down
```

### Перезапуск

```bash
# Перезапуск всех сервисов
docker-compose restart

# Перезапуск только бота
docker-compose restart bot
```

**Для bot-only:**
```bash
docker-compose -f docker-compose.bot-only.yml restart bot
```

### Обновление

```bash
# Получить новый код
git pull

# Пересобрать и перезапустить
docker-compose up -d --build
```

**Для bot-only:**
```bash
git pull
docker-compose -f docker-compose.bot-only.yml up -d --build
```

### Сброс БД

```bash
# Войти в контейнер бота
docker-compose exec bot sh

# Внутри контейнера запустить сброс
uv run python main.py --reset-db --confirm

# Выйти
exit

# Перезапустить бота
docker-compose restart bot
```

## Логи

```bash
# Все логи
docker-compose logs

# Логи бота в реальном времени
docker-compose logs -f bot

# Последние 100 строк логов
docker-compose logs --tail=100 bot

# Логи PostgreSQL
docker-compose logs postgres
```

## Резервное копирование БД

### Создание бэкапа

```bash
# Создать бэкап в файл
docker-compose exec postgres pg_dump -U yatrackerhelper yatrackerhelper > backup_$(date +%Y%m%d_%H%M%S).sql

# Или с использованием pg_dumpall для всех БД
docker-compose exec postgres pg_dumpall -U yatrackerhelper > backup_all_$(date +%Y%m%d_%H%M%S).sql
```

### Восстановление из бэкапа

```bash
# Остановить бота
docker-compose stop bot

# Восстановить БД из файла
cat backup_20251008_120000.sql | docker-compose exec -T postgres psql -U yatrackerhelper yatrackerhelper

# Запустить бота
docker-compose start bot
```

## Отладка

### Проверка здоровья контейнеров

```bash
# Проверка статуса
docker-compose ps

# Проверка healthcheck PostgreSQL
docker-compose exec postgres pg_isready -U yatrackerhelper
```

### Вход в контейнер

```bash
# Войти в контейнер бота
docker-compose exec bot sh

# Войти в контейнер PostgreSQL
docker-compose exec postgres psql -U yatrackerhelper yatrackerhelper
```

### Проверка переменных окружения

```bash
# Показать переменные окружения бота
docker-compose exec bot env | grep -E "TRACKER|BOT|DATABASE|OWNER"
```

### Проверка сети

```bash
# Проверить подключение бота к PostgreSQL
docker-compose exec bot ping -c 3 postgres
```

## Архитектура

### Сервисы

1. **postgres** - PostgreSQL 15 Alpine
   - База данных для хранения пользователей и настроек
   - Volume: `postgres_data` для персистентности
   - Healthcheck: проверка готовности каждые 10 секунд
   - Port: 5432 (внутренний)

2. **bot** - Python 3.11 Slim + uv
   - Telegram бот
   - Зависит от postgres (запускается после готовности БД)
   - Автоматическая инициализация таблиц и владельцев
   - Логирование с ротацией (max 10MB, 3 файла)

### Volumes

- `postgres_data` - данные PostgreSQL (персистентные)

### Networks

- `yatrackerhelper_network` - bridge сеть для связи между контейнерами

## Производственное развертывание

### Рекомендации

1. **Измени пароль БД:**
   ```env
   DB_PASSWORD=strong_random_password_here
   ```

2. **Настрой логирование:**
   - Логи ротируются автоматически (max 10MB, 3 файла)
   - Можно настроить через `docker-compose.yml`

3. **Мониторинг:**
   ```bash
   # Проверка ресурсов
   docker stats yatrackerhelper_bot yatrackerhelper_db
   ```

4. **Автозапуск:**
   - Политика restart: `unless-stopped`
   - Контейнеры запустятся автоматически после перезагрузки сервера

5. **Бэкапы:**
   - Настрой регулярные бэкапы PostgreSQL (см. раздел выше)
   - Используй cron для автоматизации

### Пример cron для бэкапов

```bash
# Добавь в crontab (crontab -e)
# Бэкап каждый день в 3:00
0 3 * * * cd /path/to/YaTackerHelper && docker-compose exec -T postgres pg_dump -U yatrackerhelper yatrackerhelper > /backups/yatrackerhelper_$(date +\%Y\%m\%d).sql
```

## Troubleshooting

### Бот не запускается

1. Проверь логи:
   ```bash
   docker-compose logs bot
   ```

2. Проверь переменные окружения:
   ```bash
   docker-compose exec bot env | grep -E "TRACKER|BOT|DATABASE"
   ```

3. Проверь подключение к БД:
   ```bash
   docker-compose exec bot ping postgres
   ```

### Ошибка "value out of int32 range"

Если видишь ошибку:
```
invalid input for query argument $1: 7123002827 (value out of int32 range)
```

**Причина:** Старая версия БД использовала INTEGER для telegram_id (поддержка до 2.1 млрд), но Telegram ID могут быть больше.

**Решение:**

1. **Для Docker с PostgreSQL контейнером (рекомендуется):**
   ```bash
   # Остановить и удалить контейнеры вместе с данными БД
   docker-compose down -v

   # Запустить заново (создаст новые таблицы с правильным типом)
   docker-compose up -d --build
   ```

2. **Для Docker с внешней БД через переменную окружения (проще):**
   ```bash
   # 1. Добавь в .env файл:
   echo "RESET_DB=true" >> .env

   # 2. Перезапусти контейнер
   docker-compose -f docker-compose.bot-only.yml down
   docker-compose -f docker-compose.bot-only.yml up -d

   # 3. Проверь логи
   docker-compose -f docker-compose.bot-only.yml logs -f bot

   # 4. ⚠️ ВАЖНО: После успешного запуска удали RESET_DB из .env!
   # Отредактируй .env и удали строку RESET_DB=true
   ```

3. **Для Docker с внешней БД вручную:**
   ```bash
   # Войти в контейнер
   docker-compose -f docker-compose.bot-only.yml exec bot sh

   # Сбросить БД (удалит все данные!)
   uv run python main.py --reset-db --confirm

   # Выйти
   exit

   # Перезапустить
   docker-compose -f docker-compose.bot-only.yml restart bot
   ```

4. **Ручная миграция через psql (без потери данных, для опытных):**
   ```sql
   ALTER TABLE users ALTER COLUMN telegram_id TYPE BIGINT;
   ```

### PostgreSQL не готов

1. Проверь healthcheck:
   ```bash
   docker-compose ps
   ```

2. Проверь логи PostgreSQL:
   ```bash
   docker-compose logs postgres
   ```

3. Увеличь timeout в `docker-compose.yml`:
   ```yaml
   healthcheck:
     timeout: 10s  # Было 5s
   ```

### Проблемы с permissions

```bash
# Пересоздай контейнеры
docker-compose down
docker-compose up -d --build
```

### Очистка всех данных

```bash
# Остановить и удалить все (ВНИМАНИЕ: удалит все данные!)
docker-compose down -v

# Удалить образы
docker-compose down --rmi all -v
```

## Обновление версий

### Python

Отредактируй `Dockerfile`:
```dockerfile
FROM python:3.12-slim  # Было 3.11-slim
```

### PostgreSQL

Отредактируй `docker-compose.yml`:
```yaml
postgres:
  image: postgres:16-alpine  # Было 15-alpine
```

**Важно:** При обновлении PostgreSQL может потребоваться миграция данных!

## Ссылки

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [PostgreSQL Docker](https://hub.docker.com/_/postgres)
