# Docker Commands - Шпаргалка

## Запуск

### Только веб-приложение
```bash
docker-compose -f docker-compose.web-only.yml up -d
```

### Полный стек (БД + Бот + Веб)
```bash
docker-compose -f docker-compose.full.yml up -d
```

### С пересборкой образов
```bash
docker-compose -f docker-compose.full.yml up -d --build
```

## Остановка

### Остановить и удалить контейнеры
```bash
docker-compose -f docker-compose.full.yml down
```

### Остановить, удалить контейнеры и volumes
```bash
docker-compose -f docker-compose.full.yml down -v
```

## Логи

### Все сервисы в реальном времени
```bash
docker-compose -f docker-compose.full.yml logs -f
```

### Только веб
```bash
docker logs -f yatrackerhelper_web
```

### Только бот
```bash
docker logs -f yatrackerhelper_bot
```

### Последние 100 строк
```bash
docker logs --tail 100 yatrackerhelper_web
```

## Перезапуск

### Все сервисы
```bash
docker-compose -f docker-compose.full.yml restart
```

### Только веб
```bash
docker restart yatrackerhelper_web
```

### Только бот
```bash
docker restart yatrackerhelper_bot
```

## Статус

### Статус всех контейнеров
```bash
docker-compose -f docker-compose.full.yml ps
```

### Использование ресурсов
```bash
docker stats yatrackerhelper_web yatrackerhelper_bot yatrackerhelper_db
```

## Обновление кода

```bash
# 1. Остановить
docker-compose -f docker-compose.full.yml down

# 2. Обновить код
git pull

# 3. Пересобрать и запустить
docker-compose -f docker-compose.full.yml up -d --build
```

## Отладка

### Зайти внутрь контейнера
```bash
docker exec -it yatrackerhelper_web sh
```

### Выполнить команду внутри контейнера
```bash
docker exec yatrackerhelper_web ls -la
```

### Проверить переменные окружения
```bash
docker exec yatrackerhelper_web env
```

### Проверить порты
```bash
docker exec yatrackerhelper_web netstat -tuln
```

## База данных

### Бэкап
```bash
docker exec yatrackerhelper_db pg_dump -U yatrackerhelper yatrackerhelper > backup_$(date +%Y%m%d_%H%M%S).sql
```

### Бэкап с компрессией
```bash
docker exec yatrackerhelper_db pg_dump -U yatrackerhelper yatrackerhelper | gzip > backup_$(date +%Y%m%d_%H%M%S).sql.gz
```

### Восстановление
```bash
cat backup.sql | docker exec -i yatrackerhelper_db psql -U yatrackerhelper yatrackerhelper
```

### Зайти в psql
```bash
docker exec -it yatrackerhelper_db psql -U yatrackerhelper yatrackerhelper
```

## Очистка

### Удалить неиспользуемые образы
```bash
docker image prune
```

### Удалить все (осторожно!)
```bash
docker system prune -a
```

### Удалить volumes (удалит данные БД!)
```bash
docker volume prune
```

## Health check

### Проверка веба
```bash
curl http://localhost:8000/health
# или
curl https://yatrackerhelper.yourdomain.com/health
```

### Проверка БД
```bash
docker exec yatrackerhelper_db pg_isready -U yatrackerhelper
```

## Быстрые команды

```bash
# Полный перезапуск с пересборкой
docker-compose -f docker-compose.full.yml down && \
docker-compose -f docker-compose.full.yml up -d --build && \
docker-compose -f docker-compose.full.yml logs -f

# Смотреть логи веба и бота одновременно
docker logs -f yatrackerhelper_web & docker logs -f yatrackerhelper_bot

# Проверить что все работает
docker ps | grep yatrackerhelper
```
