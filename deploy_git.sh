#!/bin/bash

# Скрипт для деплоя из Git репозитория на VPS
# Использование: ./deploy_git.sh

set -e  # Выход при ошибке

# Конфигурация
SERVER="root@95.217.187.167"
REMOTE_DIR="/home/agent/PythonAgent"
SERVICE_NAME="pythonagent"

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Функции для вывода
print_header() {
    echo -e "${BLUE}=========================================="
    echo -e "$1"
    echo -e "==========================================${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

# Деплой через Git
deploy_from_git() {
    print_info "Деплой из Git репозитория..."
    
    ssh ${SERVER} << 'EOF'
set -e

# Цвета
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

cd /home/agent/PythonAgent

echo -e "${BLUE}=== Git Pull ===${NC}"
# Сохраняем локальные изменения .env если есть
if [ -f .env ]; then
    cp .env .env.backup
    echo -e "${GREEN}✓ .env сохранен в .env.backup${NC}"
fi

# Получаем обновления
git fetch origin
git pull origin main || git pull origin master

# Восстанавливаем .env
if [ -f .env.backup ]; then
    mv .env.backup .env
    echo -e "${GREEN}✓ .env восстановлен${NC}"
fi

# Проверяем наличие .env
if [ ! -f .env ]; then
    echo -e "${RED}✗ .env не найден! Создайте файл .env с ANTHROPIC_API_KEY${NC}"
    exit 1
fi

echo -e "\n${BLUE}=== Проверка зависимостей ===${NC}"
# Активируем виртуальное окружение
source venv/bin/activate

# Проверяем, изменился ли requirements.txt
if git diff HEAD@{1} HEAD --name-only | grep -q requirements.txt; then
    echo -e "${YELLOW}⚠ requirements.txt изменился, обновляем зависимости...${NC}"
    pip install -r requirements.txt
    echo -e "${GREEN}✓ Зависимости обновлены${NC}"
else
    echo -e "${GREEN}✓ requirements.txt не изменился${NC}"
fi

deactivate

echo -e "\n${BLUE}=== Проверка .env ===${NC}"
source .env
if [ -n "$ANTHROPIC_API_KEY" ]; then
    echo -e "${GREEN}✓ ANTHROPIC_API_KEY установлен: ${ANTHROPIC_API_KEY:0:10}...${ANTHROPIC_API_KEY: -4}${NC}"
else
    echo -e "${RED}✗ ANTHROPIC_API_KEY не установлен!${NC}"
    exit 1
fi

echo -e "\n${BLUE}=== Перезапуск сервиса ===${NC}"
sudo systemctl restart pythonagent
echo -e "${GREEN}✓ Сервис перезапущен${NC}"

echo -e "\n${BLUE}=== Ожидание запуска (5 секунд) ===${NC}"
sleep 5

echo -e "\n${BLUE}=== Health Check ===${NC}"
health_response=$(curl -s http://localhost:8000/health)
if echo "$health_response" | grep -q '"status": "ok"'; then
    echo -e "${GREEN}✓ Health check успешен${NC}"
    echo "$health_response" | python3 -m json.tool
else
    echo -e "${RED}✗ Health check провален${NC}"
    echo "$health_response"
    exit 1
fi

echo -e "\n${BLUE}=== Chat Endpoint Test ===${NC}"
chat_response=$(curl -s -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"Тест деплоя из Git"}')

if echo "$chat_response" | grep -q '"reply"'; then
    echo -e "${GREEN}✓ Chat endpoint работает${NC}"
    echo "$chat_response" | python3 -m json.tool | head -20
else
    echo -e "${RED}✗ Chat endpoint не работает${NC}"
    echo "$chat_response"
    exit 1
fi

echo -e "\n${BLUE}=== Service Status ===${NC}"
systemctl status pythonagent --no-pager -l | head -15

echo -e "\n${GREEN}=========================================="
echo -e "Деплой из Git успешно завершен!"
echo -e "==========================================${NC}"
EOF
    
    if [ $? -eq 0 ]; then
        print_success "Деплой из Git успешно завершен!"
    else
        print_error "Ошибка деплоя из Git"
        exit 1
    fi
}

# Основной процесс
main() {
    print_header "Деплой PythonAgent на VPS (из Git)"
    
    deploy_from_git
    
    echo ""
    print_header "Деплой завершен успешно!"
    print_info "Сервер доступен по адресу: http://95.217.187.167:8000"
}

# Запуск
main

