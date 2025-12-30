# Исправление enum типа PaymentRequestStatus

## Проблема
PostgreSQL enum тип `paymentrequeststatus` был создан с неправильными значениями (возможно uppercase вместо lowercase).

## Решение
Применить SQL скрипт `fix_enum.sql` на сервере.

## Инструкция

### Вариант 1: Через psql (если есть прямой доступ к PostgreSQL)

```bash
# Подключитесь к базе данных
psql -U <username> -d <database_name>

# Выполните скрипт
\i fix_enum.sql

# Или одной командой:
psql -U <username> -d <database_name> -f fix_enum.sql
```

### Вариант 2: Через Docker (если БД в контейнере)

```bash
# Скопируйте SQL файл в контейнер
docker cp fix_enum.sql <postgres_container_name>:/tmp/fix_enum.sql

# Выполните скрипт в контейнере
docker exec -i <postgres_container_name> psql -U <username> -d <database_name> -f /tmp/fix_enum.sql
```

### Вариант 3: Через Python скрипт

```bash
# Запустите Python скрипт с подключением к БД
python << 'EOF'
import asyncio
import asyncpg

async def fix_enum():
    conn = await asyncpg.connect('postgresql://user:pass@host:5432/dbname')
    with open('fix_enum.sql', 'r') as f:
        sql = f.read()
    await conn.execute(sql)
    await conn.close()
    print("✅ Enum fixed successfully!")

asyncio.run(fix_enum())
EOF
```

## ⚠️ ПРЕДУПРЕЖДЕНИЕ

Этот скрипт **УДАЛИТ все существующие запросы на оплату** в таблице `payment_requests`!

Если в продакшн базе уже есть важные данные, создайте backup перед выполнением:

```bash
# Создать backup таблицы
pg_dump -U <username> -d <database_name> -t payment_requests > payment_requests_backup.sql
```

## После применения

1. Перезапустите бота:
   ```bash
   docker compose -f docker-compose.bot-only.yml restart
   ```

2. Проверьте что бот работает и можно создавать запросы на оплату

## Проверка результата

```sql
-- Проверить что enum создан правильно
SELECT enumlabel FROM pg_enum WHERE enumtypid = 'paymentrequeststatus'::regtype;

-- Должно вывести:
-- pending
-- scheduled_today
-- scheduled_date
-- paid
-- cancelled
```
