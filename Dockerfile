FROM python:3.11-slim

# Установ рабочей директории
WORKDIR /app

# Установ переменных окружения
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Установи системные зависимости
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Скопируй файлы
COPY requirements.txt .
COPY . .

# Установи Python зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Создай директорию для данных
RUN mkdir -p /app/data

# Запусти бот
CMD ["python3", "telegram_bot_v2.py"]
