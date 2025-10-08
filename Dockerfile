# Используем официальный Python образ
FROM python:3.11-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем uv из официального образа
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Копируем файлы проекта
COPY pyproject.toml uv.lock ./

# Устанавливаем зависимости через uv
RUN uv sync --frozen

# Копируем остальные файлы приложения
COPY . .

# Создаем пользователя для запуска приложения (безопасность)
RUN useradd -m -u 1000 botuser && chown -R botuser:botuser /app
USER botuser

# Команда запуска
CMD ["uv", "run", "python", "main.py"]
