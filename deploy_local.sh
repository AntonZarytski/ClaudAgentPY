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

    # Основные файлы приложения
    if [ ! -f "App.py" ]; then
        missing_files+=("App.py")
    fi

    # Модули Python (после рефакторинга)
    if [ ! -f "constants.py" ]; then
        missing_files+=("constants.py")
    fi

    if [ ! -f "prompts.py" ]; then
        missing_files+=("prompts.py")
    fi

    if [ ! -f "logger.py" ]; then
        missing_files+=("logger.py")
    fi

    if [ ! -f "claude_client.py" ]; then
        missing_files+=("claude_client.py")
    fi

    if [ ! -f "token_counter.py" ]; then
        missing_files+=("token_counter.py")
    fi

    if [ ! -f "history_compression.py" ]; then
        missing_files+=("history_compression.py")
    fi

    if [ ! -f "conversations.db" ]; then
        missing_files+=("conversations.db")
    fi

    if [ ! -f "database.py" ]; then
        missing_files+=("database.py")
    fi

    # Фронтенд
    if [ ! -f "public/index.html" ]; then
        missing_files+=("public/index.html")
    fi

    # Зависимости
    if [ ! -f "requirements.txt" ]; then
        missing_files+=("requirements.txt")
    fi

    # .env файл
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

    # Копируем основной файл приложения
    if scp -q App.py ${SERVER}:${REMOTE_DIR}/; then
        print_success "App.py скопирован"
    else
        print_error "Ошибка копирования App.py"
        exit 1
    fi

    # Копируем модули Python (после рефакторинга)
    print_info "Копирование модулей Python..."

    if scp -q constants.py ${SERVER}:${REMOTE_DIR}/; then
        print_success "constants.py скопирован"
    else
        print_error "Ошибка копирования constants.py"
        exit 1
    fi

    if scp -q prompts.py ${SERVER}:${REMOTE_DIR}/; then
        print_success "prompts.py скопирован"
    else
        print_error "Ошибка копирования prompts.py"
        exit 1
    fi

    if scp -q logger.py ${SERVER}:${REMOTE_DIR}/; then
        print_success "logger.py скопирован"
    else
        print_error "Ошибка копирования logger.py"
        exit 1
    fi

    if scp -q claude_client.py ${SERVER}:${REMOTE_DIR}/; then
        print_success "claude_client.py скопирован"
    else
        print_error "Ошибка копирования claude_client.py"
        exit 1
    fi

    if scp -q token_counter.py ${SERVER}:${REMOTE_DIR}/; then
        print_success "token_counter.py скопирован"
    else
        print_error "Ошибка копирования token_counter.py"
        exit 1
    fi

    if scp -q history_compression.py ${SERVER}:${REMOTE_DIR}/; then
        print_success "history_compression.py скопирован"
    else
        print_error "Ошибка копирования history_compression.py"
        exit 1
    fi

    if scp -q conversations.db ${SERVER}:${REMOTE_DIR}/; then
        print_success "conversations.db скопирован"
    else
        print_error "Ошибка копирования conversations.db"
        exit 1
    fi

    if scp -q database.py ${SERVER}:${REMOTE_DIR}/; then
        print_success "database.py скопирован"
    else
        print_error "Ошибка копирования database.py"
        exit 1
    fi

    # Копируем .env
    if scp -q .env ${SERVER}:${REMOTE_DIR}/; then
        print_success ".env скопирован"
    else
        print_error "Ошибка копирования .env"
        exit 1
    fi

    # Копируем requirements.txt
    if scp -q requirements.txt ${SERVER}:${REMOTE_DIR}/; then
        print_success "requirements.txt скопирован"
    else
        print_error "Ошибка копирования requirements.txt"
        exit 1
    fi

    # Копируем фронтенд
    print_info "Копирование фронтенда..."
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

# Обновление зависимостей на сервере
update_dependencies() {
    print_info "Проверка и обновление зависимостей..."

    ssh ${SERVER} << EOF
cd ${REMOTE_DIR}

# Активируем виртуальное окружение
source venv/bin/activate

# Обновляем зависимости
echo -e "${BLUE}Обновление зависимостей из requirements.txt...${NC}"
pip install -r requirements.txt --quiet

if [ \$? -eq 0 ]; then
    echo -e "${GREEN}✓ Зависимости обновлены${NC}"
else
    echo -e "${RED}✗ Ошибка обновления зависимостей${NC}"
    exit 1
fi

deactivate
EOF

    if [ $? -eq 0 ]; then
        print_success "Зависимости обновлены"
    else
        print_error "Ошибка обновления зависимостей"
        exit 1
    fi
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

# Chat endpoint test - Default format
echo -e "\n${BLUE}=== Chat Endpoint Test (Default) ===${NC}"
chat_response=$(curl -s -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"Привет! Это тест деплоя.","output_format":"default"}')

if echo "$chat_response" | grep -q '"reply"'; then
    echo -e "${GREEN}✓ Chat endpoint (default) работает${NC}"
    echo "$chat_response" | python3 -m json.tool | head -20
else
    echo -e "${RED}✗ Chat endpoint (default) не работает${NC}"
    echo "$chat_response"
    exit 1
fi

# Chat endpoint test - JSON format
echo -e "\n${BLUE}=== Chat Endpoint Test (JSON) ===${NC}"
json_response=$(curl -s -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"Что такое Python?","output_format":"json"}')

if echo "$json_response" | grep -q '"reply"'; then
    echo -e "${GREEN}✓ Chat endpoint (json) работает${NC}"
    # Проверяем, что ответ содержит JSON
    if echo "$json_response" | python3 -c "import sys, json; data=json.load(sys.stdin); reply=data['reply']; json.loads(reply)" 2>/dev/null; then
        echo -e "${GREEN}✓ Ответ содержит валидный JSON${NC}"
    else
        echo -e "${YELLOW}⚠ Ответ может не содержать валидный JSON${NC}"
    fi
else
    echo -e "${RED}✗ Chat endpoint (json) не работает${NC}"
    echo "$json_response"
fi

# Chat endpoint test - XML format
echo -e "\n${BLUE}=== Chat Endpoint Test (XML) ===${NC}"
xml_response=$(curl -s -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"Что такое Python?","output_format":"xml"}')

if echo "$xml_response" | grep -q '"reply"'; then
    echo -e "${GREEN}✓ Chat endpoint (xml) работает${NC}"
    # Проверяем, что ответ содержит XML
    if echo "$xml_response" | python3 -c "import sys, json; data=json.load(sys.stdin); reply=data['reply']; assert '<?xml' in reply or '<response>' in reply" 2>/dev/null; then
        echo -e "${GREEN}✓ Ответ содержит XML${NC}"
    else
        echo -e "${YELLOW}⚠ Ответ может не содержать XML${NC}"
    fi
else
    echo -e "${RED}✗ Chat endpoint (xml) не работает${NC}"
    echo "$xml_response"
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

    update_dependencies
    echo ""

    restart_service
    echo ""

    verify_deployment
    echo ""

    print_header "Деплой завершен успешно!"
    print_info "Сервер доступен по адресу: http://95.217.187.167:8000"
    print_info "Все модули Python обновлены: App.py, constants.py, prompts.py, logger.py, claude_client.py"
    print_info "Все форматы вывода протестированы: default, json, xml"
}

# Запуск
main

