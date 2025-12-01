#!/bin/bash

# Скрипт для деплоя с локальной машины на VPS
# Использование: ./deploy_local.sh

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

# Проверка наличия необходимых файлов
check_local_files() {
    print_info "Проверка локальных файлов..."
    
    local missing_files=()
    
    if [ ! -f "App.py" ]; then
        missing_files+=("App.py")
    fi
    
    if [ ! -f "public/index.html" ]; then
        missing_files+=("public/index.html")
    fi
    
    if [ ! -f ".env" ]; then
        print_warning ".env файл не найден!"
        read -p "Создать .env файл сейчас? (y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            read -p "Введите ваш ANTHROPIC_API_KEY: " api_key
            echo "ANTHROPIC_API_KEY=$api_key" > .env
            print_success ".env файл создан"
        else
            missing_files+=(".env")
        fi
    fi
    
    if [ ${#missing_files[@]} -ne 0 ]; then
        print_error "Отсутствуют файлы: ${missing_files[*]}"
        exit 1
    fi
    
    print_success "Все необходимые файлы найдены"
}

# Копирование файлов на сервер
deploy_files() {
    print_info "Копирование файлов на сервер..."
    
    # Копируем App.py
    if scp -q App.py ${SERVER}:${REMOTE_DIR}/; then
        print_success "App.py скопирован"
    else
        print_error "Ошибка копирования App.py"
        exit 1
    fi
    
    # Копируем .env
    if scp -q .env ${SERVER}:${REMOTE_DIR}/; then
        print_success ".env скопирован"
    else
        print_error "Ошибка копирования .env"
        exit 1
    fi
    
    # Копируем index.html
    if scp -q public/index.html ${SERVER}:${REMOTE_DIR}/public/; then
        print_success "index.html скопирован"
    else
        print_error "Ошибка копирования index.html"
        exit 1
    fi
}

# Проверка .env на сервере
verify_env() {
    print_info "Проверка .env на сервере..."
    
    ssh ${SERVER} << EOF
cd ${REMOTE_DIR}
if [ -f .env ]; then
    source .env
    if [ -n "\$ANTHROPIC_API_KEY" ]; then
        echo -e "${GREEN}✓ ANTHROPIC_API_KEY установлен: \${ANTHROPIC_API_KEY:0:10}...\${ANTHROPIC_API_KEY: -4}${NC}"
        exit 0
    else
        echo -e "${RED}✗ ANTHROPIC_API_KEY пустой!${NC}"
        exit 1
    fi
else
    echo -e "${RED}✗ .env не найден на сервере!${NC}"
    exit 1
fi
EOF
}

# Перезапуск сервиса
restart_service() {
    print_info "Перезапуск сервиса ${SERVICE_NAME}..."
    
    if ssh ${SERVER} "systemctl restart ${SERVICE_NAME}"; then
        print_success "Сервис перезапущен"
    else
        print_error "Ошибка перезапуска сервиса"
        exit 1
    fi
    
    print_info "Ожидание запуска сервера (5 секунд)..."
    sleep 5
}

# Проверка работы сервера
verify_deployment() {
    print_info "Проверка работы сервера..."
    
    ssh ${SERVER} << 'EOF'
cd /home/agent/PythonAgent

# Health check
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

# Chat endpoint test
echo -e "\n${BLUE}=== Chat Endpoint Test ===${NC}"
chat_response=$(curl -s -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"Привет! Это тест деплоя."}')

if echo "$chat_response" | grep -q '"reply"'; then
    echo -e "${GREEN}✓ Chat endpoint работает${NC}"
    echo "$chat_response" | python3 -m json.tool | head -20
else
    echo -e "${RED}✗ Chat endpoint не работает${NC}"
    echo "$chat_response"
    exit 1
fi

# Статус сервиса
echo -e "\n${BLUE}=== Service Status ===${NC}"
systemctl status pythonagent --no-pager -l | head -15
EOF
    
    if [ $? -eq 0 ]; then
        print_success "Деплой успешно завершен!"
    else
        print_error "Проверка деплоя провалена"
        exit 1
    fi
}

# Основной процесс
main() {
    print_header "Деплой PythonAgent на VPS (локальные файлы)"
    
    check_local_files
    echo ""
    
    deploy_files
    echo ""
    
    verify_env
    echo ""
    
    restart_service
    echo ""
    
    verify_deployment
    echo ""
    
    print_header "Деплой завершен успешно!"
    print_info "Сервер доступен по адресу: http://95.217.187.167:8000"
}

# Запуск
main

