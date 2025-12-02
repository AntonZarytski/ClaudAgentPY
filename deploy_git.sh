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

echo -e "${BLUE}=== Git Configuration ===${NC}"
# Добавляем директорию в список безопасных для Git
git config --global --add safe.directory /home/agent/PythonAgent
echo -e "${GREEN}✓ Директория добавлена в safe.directory${NC}"

echo -e "\n${BLUE}=== Подготовка к Git Pull ===${NC}"

# Сохраняем локальные изменения .env если есть
if [ -f .env ]; then
    cp .env .env.backup
    echo -e "${GREEN}✓ .env сохранен в .env.backup${NC}"
fi

# Проверяем наличие локальных изменений (кроме .env)
echo -e "\n${BLUE}=== Проверка локальных изменений ===${NC}"
LOCAL_CHANGES=$(git status --porcelain | grep -v "\.env" | grep -v "\.env\.backup" || true)

if [ -n "$LOCAL_CHANGES" ]; then
    echo -e "${YELLOW}⚠ Обнаружены локальные изменения:${NC}"
    echo "$LOCAL_CHANGES"

    # Сохраняем локальные изменения в stash
    echo -e "\n${BLUE}Сохранение изменений в git stash...${NC}"
    STASH_MESSAGE="deploy_git.sh auto-stash $(date '+%Y-%m-%d %H:%M:%S')"
    git stash push -m "$STASH_MESSAGE" --include-untracked
    echo -e "${GREEN}✓ Локальные изменения сохранены в stash${NC}"
    STASH_CREATED=true
else
    echo -e "${GREEN}✓ Локальных изменений нет${NC}"
    STASH_CREATED=false
fi

# Получаем обновления из Git
echo -e "\n${BLUE}=== Git Pull ===${NC}"
git fetch origin
echo -e "${GREEN}✓ git fetch выполнен${NC}"

# Pull только из main ветки
if git pull origin main; then
    echo -e "${GREEN}✓ git pull origin main выполнен успешно${NC}"
else
    echo -e "${RED}✗ Ошибка при git pull origin main${NC}"

    # Если был создан stash, восстанавливаем его
    if [ "$STASH_CREATED" = true ]; then
        echo -e "${YELLOW}⚠ Восстановление локальных изменений из stash...${NC}"
        git stash pop || true
    fi

    # Восстанавливаем .env
    if [ -f .env.backup ]; then
        mv .env.backup .env
    fi

    exit 1
fi

# Восстанавливаем локальные изменения из stash (если были)
if [ "$STASH_CREATED" = true ]; then
    echo -e "\n${BLUE}=== Восстановление локальных изменений ===${NC}"

    if git stash pop; then
        echo -e "${GREEN}✓ Локальные изменения восстановлены из stash${NC}"
    else
        echo -e "${YELLOW}⚠ Конфликт при восстановлении stash${NC}"
        echo -e "${YELLOW}  Изменения остались в stash. Используйте 'git stash list' для просмотра${NC}"
        echo -e "${YELLOW}  и 'git stash drop' для удаления после ручного разрешения конфликтов${NC}"
    fi
fi

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

echo -e "\n${BLUE}=== Проверка файлов проекта ===${NC}"
# Проверяем наличие всех необходимых файлов после git pull
required_files=("App.py" "constants.py" "prompts.py" "logger.py" "claude_client.py" "public/index.html" "requirements.txt")
missing_files=()

for file in "${required_files[@]}"; do
    if [ ! -f "$file" ]; then
        missing_files+=("$file")
    fi
done

if [ ${#missing_files[@]} -ne 0 ]; then
    echo -e "${RED}✗ Отсутствуют файлы: ${missing_files[*]}${NC}"
    exit 1
else
    echo -e "${GREEN}✓ Все необходимые файлы найдены${NC}"
    echo -e "${GREEN}  - App.py${NC}"
    echo -e "${GREEN}  - constants.py${NC}"
    echo -e "${GREEN}  - prompts.py${NC}"
    echo -e "${GREEN}  - logger.py${NC}"
    echo -e "${GREEN}  - claude_client.py${NC}"
    echo -e "${GREEN}  - public/index.html${NC}"
    echo -e "${GREEN}  - requirements.txt${NC}"
fi

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

echo -e "\n${BLUE}=== Chat Endpoint Test (Default) ===${NC}"
chat_response=$(curl -s -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"Тест деплоя из Git","output_format":"default"}')

if echo "$chat_response" | grep -q '"reply"'; then
    echo -e "${GREEN}✓ Chat endpoint (default) работает${NC}"
    echo "$chat_response" | python3 -m json.tool | head -20
else
    echo -e "${RED}✗ Chat endpoint (default) не работает${NC}"
    echo "$chat_response"
    exit 1
fi

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

