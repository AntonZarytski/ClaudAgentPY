#!/bin/bash

# Скрипт для настройки SSH agent для автоматической аутентификации
# Использование: ./setup_ssh.sh

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

# Проверка наличия SSH ключа
check_ssh_key() {
    if [ -f ~/.ssh/id_ed25519 ]; then
        print_success "SSH ключ найден: ~/.ssh/id_ed25519"
        return 0
    else
        print_error "SSH ключ не найден: ~/.ssh/id_ed25519"
        return 1
    fi
}

# Настройка SSH agent
setup_ssh_agent() {
    print_info "Настройка SSH agent..."
    
    # Проверяем, запущен ли ssh-agent
    if [ -z "$SSH_AUTH_SOCK" ]; then
        print_warning "SSH agent не запущен, запускаем..."
        eval "$(ssh-agent -s)"
        print_success "SSH agent запущен"
    else
        print_success "SSH agent уже запущен"
    fi
    
    # Добавляем ключ в ssh-agent
    print_info "Добавление ключа в ssh-agent..."
    ssh-add ~/.ssh/id_ed25519
    
    if [ $? -eq 0 ]; then
        print_success "Ключ добавлен в ssh-agent"
    else
        print_error "Ошибка добавления ключа в ssh-agent"
        return 1
    fi
    
    # Проверяем добавленные ключи
    print_info "Список ключей в ssh-agent:"
    ssh-add -l
}

# Создание SSH config
create_ssh_config() {
    print_info "Создание SSH config..."
    
    SSH_CONFIG=~/.ssh/config
    
    # Создаем backup если файл существует
    if [ -f "$SSH_CONFIG" ]; then
        cp "$SSH_CONFIG" "${SSH_CONFIG}.backup.$(date +%Y%m%d_%H%M%S)"
        print_success "Создан backup: ${SSH_CONFIG}.backup"
    fi
    
    # Проверяем, есть ли уже настройка для нашего сервера
    if grep -q "Host hetzner-vps" "$SSH_CONFIG" 2>/dev/null; then
        print_warning "Настройка для hetzner-vps уже существует в SSH config"
    else
        # Добавляем настройку
        cat >> "$SSH_CONFIG" << 'EOF'

# PythonAgent VPS Server
Host hetzner-vps
    HostName 95.217.187.167
    User root
    IdentityFile ~/.ssh/id_ed25519
    AddKeysToAgent yes
    UseKeychain yes
    ServerAliveInterval 60
    ServerAliveCountMax 3
EOF
        print_success "Настройка добавлена в SSH config"
    fi
    
    # Устанавливаем правильные права
    chmod 600 "$SSH_CONFIG"
    print_success "Права на SSH config установлены (600)"
}

# Настройка автозагрузки ssh-agent в .zshrc или .bashrc
setup_shell_config() {
    print_info "Настройка автозагрузки ssh-agent в shell..."
    
    # Определяем, какой shell используется
    if [ -n "$ZSH_VERSION" ] || [ -f ~/.zshrc ]; then
        SHELL_CONFIG=~/.zshrc
        SHELL_NAME="zsh"
    else
        SHELL_CONFIG=~/.bashrc
        SHELL_NAME="bash"
    fi
    
    print_info "Используется shell: $SHELL_NAME"
    
    # Проверяем, есть ли уже настройка
    if grep -q "ssh-agent" "$SHELL_CONFIG" 2>/dev/null; then
        print_warning "Настройка ssh-agent уже существует в $SHELL_CONFIG"
    else
        # Добавляем настройку
        cat >> "$SHELL_CONFIG" << 'EOF'

# SSH Agent auto-start
if [ -z "$SSH_AUTH_SOCK" ]; then
    eval "$(ssh-agent -s)" > /dev/null
    ssh-add ~/.ssh/id_ed25519 2>/dev/null
fi
EOF
        print_success "Настройка добавлена в $SHELL_CONFIG"
        print_info "Перезапустите терминал или выполните: source $SHELL_CONFIG"
    fi
}

# Тест подключения
test_connection() {
    print_info "Тестирование подключения к серверу..."
    
    if ssh -o BatchMode=yes -o ConnectTimeout=5 hetzner-vps "echo 'Connection successful'" 2>/dev/null; then
        print_success "Подключение к серверу успешно (без ввода пароля)!"
    else
        print_warning "Подключение требует ввода пароля"
        print_info "Попробуйте подключиться вручную: ssh hetzner-vps"
    fi
}

# Основной процесс
main() {
    print_header "Настройка SSH для автоматической аутентификации"
    
    if ! check_ssh_key; then
        print_error "Сначала создайте SSH ключ: ssh-keygen -t ed25519"
        exit 1
    fi
    
    echo ""
    setup_ssh_agent
    
    echo ""
    create_ssh_config
    
    echo ""
    setup_shell_config
    
    echo ""
    test_connection
    
    echo ""
    print_header "Настройка завершена!"
    
    echo ""
    print_info "Теперь вы можете использовать:"
    echo "  ssh hetzner-vps                    # Подключение к серверу"
    echo "  ./deploy_local.sh                  # Деплой локальных файлов"
    echo "  ./deploy_git.sh                    # Деплой из Git"
    echo "  ./get_logs.sh                      # Получение логов"
    
    echo ""
    print_warning "Если ssh-agent не работает после перезапуска терминала,"
    print_warning "выполните: source $SHELL_CONFIG"
}

# Запуск
main

