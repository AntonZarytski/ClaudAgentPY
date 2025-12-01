#!/bin/bash

# Скрипт для получения логов с VPS сервера
# Использование: ./get_logs.sh [количество_строк]

# Конфигурация
SERVER="root@95.217.187.167"
REMOTE_DIR="/home/agent/PythonAgent"
SERVICE_NAME="pythonagent"

# Количество строк для вывода (по умолчанию 100)
LINES=${1:-100}

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color

# Функции для вывода
print_header() {
    echo -e "${BLUE}=========================================="
    echo -e "$1"
    echo -e "==========================================${NC}"
}

print_section() {
    echo -e "\n${MAGENTA}=== $1 ===${NC}"
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

# Получение логов
get_logs() {
    ssh ${SERVER} << EOF
# Цвета
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
NC='\033[0m'

echo -e "\${MAGENTA}=== Статус сервиса ${SERVICE_NAME} ===\${NC}"
systemctl status ${SERVICE_NAME} --no-pager -l | head -20

echo -e "\n\${MAGENTA}=== Процессы Gunicorn ===\${NC}"
ps aux | grep -E "gunicorn|PID" | grep -v grep

echo -e "\n\${MAGENTA}=== Порт 8000 ===\${NC}"
ss -tlnp | grep :8000 || echo "Порт 8000 не слушается"

echo -e "\n\${MAGENTA}=== Health Check ===\${NC}"
health_response=\$(curl -s http://localhost:8000/health)
if echo "\$health_response" | grep -q '"status"'; then
    echo -e "\${GREEN}✓ Сервер отвечает\${NC}"
    echo "\$health_response" | python3 -m json.tool
else
    echo -e "\${RED}✗ Сервер не отвечает\${NC}"
    echo "\$health_response"
fi

echo -e "\n\${MAGENTA}=== Последние ${LINES} строк из journalctl ===\${NC}"
journalctl -u ${SERVICE_NAME} -n ${LINES} --no-pager

echo -e "\n\${MAGENTA}=== Файл app.log (если существует) ===\${NC}"
if [ -f ${REMOTE_DIR}/app.log ]; then
    echo -e "\${GREEN}✓ app.log найден\${NC}"
    echo "Последние 50 строк:"
    tail -n 50 ${REMOTE_DIR}/app.log
else
    echo -e "\${YELLOW}⚠ app.log не найден\${NC}"
fi

echo -e "\n\${MAGENTA}=== Последние ошибки из логов ===\${NC}"
journalctl -u ${SERVICE_NAME} -n 200 --no-pager | grep -i -E "error|critical|exception|failed" | tail -20 || echo "Ошибок не найдено"

echo -e "\n\${MAGENTA}=== Проверка .env ===\${NC}"
cd ${REMOTE_DIR}
if [ -f .env ]; then
    echo -e "\${GREEN}✓ .env существует\${NC}"
    source .env
    if [ -n "\$ANTHROPIC_API_KEY" ]; then
        echo -e "\${GREEN}✓ ANTHROPIC_API_KEY установлен: \${ANTHROPIC_API_KEY:0:10}...\${ANTHROPIC_API_KEY: -4}\${NC}"
    else
        echo -e "\${RED}✗ ANTHROPIC_API_KEY пустой!\${NC}"
    fi
else
    echo -e "\${RED}✗ .env не найден!\${NC}"
fi

echo -e "\n\${MAGENTA}=== Использование ресурсов ===\${NC}"
echo "Память:"
free -h | grep -E "Mem|Swap"
echo ""
echo "Диск:"
df -h / | grep -E "Filesystem|/"
echo ""
echo "CPU Load:"
uptime

echo -e "\n\${MAGENTA}=== Последние 10 запросов к API ===\${NC}"
journalctl -u ${SERVICE_NAME} -n 500 --no-pager | grep "Получен запрос на /api/chat" | tail -10 || echo "Запросов не найдено"
EOF
}

# Основной процесс
main() {
    print_header "Логи PythonAgent на VPS"
    print_info "Получение последних ${LINES} строк логов..."
    echo ""
    
    get_logs
    
    echo ""
    print_header "Получение логов завершено"
    print_info "Для просмотра логов в реальном времени используйте:"
    echo "  ssh ${SERVER} 'journalctl -u ${SERVICE_NAME} -f'"
}

# Запуск
main

