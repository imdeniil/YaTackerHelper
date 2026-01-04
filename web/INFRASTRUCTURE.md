# Инфраструктура веб-приложения

## 📁 Созданная структура

```
YaTackerHelper/
├── web/                           # Веб-приложение FastHTML
│   ├── __init__.py
│   ├── app.py                     # Основное приложение
│   ├── config.py                  # Конфигурация (WebConfig)
│   ├── database.py                # Подключение к БД (переиспользует bot/database)
│   ├── routes/                    # Маршруты
│   │   ├── __init__.py
│   │   ├── auth.py               # Авторизация через Telegram Login Widget
│   │   └── dashboard.py          # Dashboard по ролям (в разработке)
│   ├── static/                    # Статические файлы
│   ├── README.md                  # Документация веба
│   └── INFRASTRUCTURE.md          # Этот файл
│
├── run_web.py                     # Скрипт запуска веб-приложения
│
├── Dockerfile.web                 # Docker образ для веба
├── docker-compose.web-only.yml    # Запуск только веба
├── docker-compose.full.yml        # Запуск полного стека (БД + Бот + Веб)
│
├── DEPLOYMENT.md                  # Полная документация по деплою
├── QUICKSTART_DEPLOY.md           # Быстрый старт для деплоя
└── DOCKER_COMMANDS.md             # Шпаргалка по Docker командам
```

## 🏗️ Архитектура

### Разделение на процессы

```
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│   Telegram Bot  │      │  Web FastHTML   │      │   PostgreSQL    │
│   (aiogram)     │◄────►│   (uvicorn)     │◄────►│                 │
│   main.py       │      │   run_web.py    │      │   Port 5432     │
│   Port: N/A     │      │   Port 8000     │      │                 │
└─────────────────┘      └─────────────────┘      └─────────────────┘
        │                        │
        │                        │
        │                        ▼
        │              ┌─────────────────┐
        │              │   Nginx-Proxy   │
        │              │   + Let's       │
        │              │   Encrypt       │
        └─────────────►│                 │
         (уведомления) │   Port 80/443   │
                       └─────────────────┘
```

### Общие ресурсы

**База данных:**
- Bot и Web используют **одну и ту же PostgreSQL БД**
- Модели: `bot/database/models.py`
- CRUD: `bot/database/crud.py`
- Отдельные engines, но одна БД

**Telegram Bot API:**
- Веб отправляет уведомления через Bot API
- Веб загружает файлы через Bot API (в приватную группу)
- Получает `file_id` для хранения в БД

## 🔐 Авторизация

### Telegram Login Widget Flow

```
1. User clicks "Login with Telegram"
   │
2. Telegram Widget возвращает:
   │  - id (telegram_id)
   │  - first_name, last_name, username
   │  - hash (HMAC-SHA256 подпись)
   │  - auth_date
   │
3. POST /auth/telegram
   │  ├─ Проверка hash (verify_telegram_auth)
   │  │  └─ secret_key = SHA256(bot_token)
   │  │  └─ calculated_hash == provided_hash
   │  │
   │  ├─ Поиск пользователя в БД (UserCRUD.get_user_by_telegram_id)
   │  │  └─ Если не найден → "Доступ запрещен"
   │  │
   │  └─ Создание сессии (cookies)
   │     ├─ sess['user_id']
   │     ├─ sess['role']
   │     └─ sess['is_billing_contact']
   │
4. Redirect → /dashboard
```

### Защита маршрутов

Декоратор `@require_auth` проверяет наличие `sess['user_id']`.

## 🐳 Docker конфигурации

### 1. docker-compose.web-only.yml

**Назначение:** Запуск только веб-приложения

**Когда использовать:**
- Бот уже запущен отдельно
- БД уже существует (на другом сервере или локально)

**Подключение:**
- Сеть: `proxy` (внешняя, для nginx-proxy)
- DATABASE_URL из `.env` (к внешней БД)

**Переменные окружения:**
```bash
VIRTUAL_HOST=yatrackerhelper.yourdomain.com
LETSENCRYPT_HOST=yatrackerhelper.yourdomain.com
LETSENCRYPT_EMAIL=your@email.com
VIRTUAL_PORT=8000
```

### 2. docker-compose.full.yml

**Назначение:** Полный стек - БД + Бот + Веб

**Когда использовать:**
- Свежий деплой
- Все компоненты на одном сервере
- Максимальная простота

**Подключение:**
- Сети:
  - `yatrackerhelper_network` (внутренняя, для БД ↔ Бот ↔ Веб)
  - `proxy` (внешняя, для nginx-proxy ↔ Веб)
- DATABASE_URL: `postgresql+asyncpg://yatrackerhelper:${DB_PASSWORD}@postgres:5432/yatrackerhelper`

**Volumes:**
- `postgres_data` - данные БД
- `certs`, `html`, `acme` - для Let's Encrypt

## 🌐 Nginx-Proxy интеграция

### Предварительные требования

На сервере должны быть запущены:

```bash
docker network create proxy

docker run -d --name nginx-proxy \
  --network proxy -p 80:80 -p 443:443 \
  -v /var/run/docker.sock:/tmp/docker.sock:ro \
  -v certs:/etc/nginx/certs \
  -v html:/usr/share/nginx/html \
  nginxproxy/nginx-proxy

docker run -d --name nginx-proxy-acme \
  --network proxy \
  --volumes-from nginx-proxy \
  -v /var/run/docker.sock:/var/run/docker.sock:ro \
  -v acme:/etc/acme.sh \
  -e DEFAULT_EMAIL=your@email.com \
  nginxproxy/acme-companion
```

### Как это работает

1. Веб-контейнер подключен к сети `proxy`
2. Nginx-proxy автоматически обнаруживает контейнер через Docker socket
3. Читает переменные окружения (`VIRTUAL_HOST`, `VIRTUAL_PORT`)
4. Создает конфигурацию Nginx для проксирования
5. Acme-companion запрашивает SSL сертификат от Let's Encrypt
6. Сертификат автоматически обновляется каждые 90 дней

## 📋 Переменные окружения

### Обязательные для веба

```bash
# Bot (для отправки уведомлений и файлов)
BOT_TOKEN=your_bot_token

# Database
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/yatrackerhelper

# Web
WEB_SECRET_KEY=your_random_secret_key  # для сессий
STORAGE_CHAT_ID=-1001234567890        # приватная группа для файлов
```

### Для деплоя с nginx-proxy

```bash
VIRTUAL_HOST=yatrackerhelper.yourdomain.com
LETSENCRYPT_HOST=yatrackerhelper.yourdomain.com
LETSENCRYPT_EMAIL=your@email.com
```

### Опциональные

```bash
WEB_PORT=8000              # по умолчанию 8000
WEB_HOST=0.0.0.0          # по умолчанию 0.0.0.0
```

## 🔄 CI/CD (будущее)

### GitHub Actions (рекомендуется)

```yaml
# .github/workflows/deploy.yml
name: Deploy to Server

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to server
        uses: appleboy/ssh-action@master
        with:
          host: ${{ secrets.SERVER_HOST }}
          username: ${{ secrets.SERVER_USER }}
          key: ${{ secrets.SERVER_SSH_KEY }}
          script: |
            cd ~/YaTackerHelper
            git pull
            docker-compose -f docker-compose.full.yml up -d --build
```

## 📊 Мониторинг

### Health check endpoint

```bash
GET /health

Response:
{
  "status": "ok",
  "service": "YaTackerHelper Web"
}
```

### Логирование

- JSON формат
- Ротация: max-size 10MB, max-file 3
- Путь: `docker logs yatrackerhelper_web`

### Метрики (планируется)

- Prometheus + Grafana
- Метрики: количество запросов, время ответа, активные пользователи

## 🚀 Следующие шаги

1. ✅ Базовая инфраструктура
2. ✅ Авторизация через Telegram
3. ⏳ Dashboard для Worker (создание запросов)
4. ⏳ Dashboard для Billing Contact (оплата)
5. ⏳ Dashboard для Owner/Manager (управление)
6. ⏳ CRUD операции для запросов
7. ⏳ Загрузка файлов через Telegram Bot API
8. ⏳ WebSockets для real-time обновлений
9. ⏳ Уведомления в Telegram

## 📚 Ссылки

- [web/README.md](README.md) - документация веб-части
