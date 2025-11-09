FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY yasno_api.py .
COPY database.py .
COPY schedule_analyzer.py .
COPY telegram_bot_v2.py .

# Create volume mount point for database
VOLUME ["/app/data"]

# Set environment variable for database location
ENV DB_PATH=/app/data/users.db

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('https://api.telegram.org/bot', timeout=5)" || exit 1

# Run the bot
CMD ["python", "telegram_bot_v2.py"]
