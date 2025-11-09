#!/bin/bash

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🤖 Yasno Bot Launcher${NC}\n"

# Check if .env exists
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚠️  .env файл не знайдено${NC}"
    echo "Створюю .env з .env.example..."
    cp .env.example .env
    echo -e "${YELLOW}⚠️  ВАЖЛИВО: Відредагуй .env и вставь свій TELEGRAM_BOT_TOKEN${NC}"
    echo "Помилка: Запусти бот знову після конфігурації."
    exit 1
fi

# Check if TELEGRAM_BOT_TOKEN is set
TOKEN=$(grep TELEGRAM_BOT_TOKEN .env | cut -d '=' -f 2)
if [ -z "$TOKEN" ] || [ "$TOKEN" = "YOUR_BOT_TOKEN_HERE" ]; then
    echo -e "${RED}❌ Помилка: TELEGRAM_BOT_TOKEN не встановлено або має значення за замовчуванням${NC}"
    echo "Відредагуй .env файл і вставь свій токен від @BotFather"
    exit 1
fi

echo -e "${GREEN}✅ Конфігурація перевірена${NC}\n"

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker не встановлений${NC}"
    echo "Встанови Docker: https://docs.docker.com/get-docker/"
    exit 1
fi

echo -e "${GREEN}✅ Docker знайдено${NC}\n"

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}❌ Docker Compose не встановлений${NC}"
    echo "Встанови Docker Compose: https://docs.docker.com/compose/install/"
    exit 1
fi

echo -e "${GREEN}✅ Docker Compose знайдено${NC}\n"

# Display menu
echo -e "${YELLOW}Виберіть опцію:${NC}"
echo "1. Запустити бота (docker-compose up -d)"
echo "2. Зупинити бота (docker-compose down)"
echo "3. Переглянути логи (docker-compose logs -f)"
echo "4. Перезапустити бота (docker-compose restart)"
echo "5. Видалити контейнер та том (docker-compose down -v)"
echo ""

read -p "Введи номер (1-5): " choice

case $choice in
    1)
        echo -e "\n${GREEN}🚀 Запускаю бота...${NC}"
        docker-compose up -d
        echo -e "${GREEN}✅ Бот запущений!${NC}"
        echo "Перевір логи: docker-compose logs -f"
        ;;
    2)
        echo -e "\n${YELLOW}⏹️  Зупиняю бота...${NC}"
        docker-compose down
        echo -e "${GREEN}✅ Бот зупинений!${NC}"
        ;;
    3)
        echo -e "\n${YELLOW}📋 Логи бота:${NC}"
        docker-compose logs -f
        ;;
    4)
        echo -e "\n${YELLOW}🔄 Перезапускаю бота...${NC}"
        docker-compose restart
        echo -e "${GREEN}✅ Бот перезапущений!${NC}"
        ;;
    5)
        echo -e "\n${RED}⚠️  Видалю контейнер та том (база даних буде видалена!)${NC}"
        read -p "Ти впевнений? (y/n): " confirm
        if [ "$confirm" = "y" ]; then
            docker-compose down -v
            echo -e "${GREEN}✅ Видалено!${NC}"
        else
            echo "Скасовано."
        fi
        ;;
    *)
        echo -e "${RED}❌ Невалідний вибір${NC}"
        exit 1
        ;;
esac
