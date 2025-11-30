# Claude Chat Agent

Простой веб-чат с использованием Claude API (Anthropic) и Flask.

Этот README описывает:
- настройку окружения локально;
- подготовку и настройку VPS-сервера (Hetzner);
- команды для логина на сервер;
- деплой и перезапуск сервиса.

---
Hetzner:
    https://console.hetzner.com/projects
Anthropic:
    https://platform.claude.com/settings/workspaces/default/keys
---

## 1. Локальная установка и запуск

### 1.1. Зависимости

Нужно:
- Python 3 (3.9+);
- `pip`.

### 1.2. Создание виртуального окружения

```bash
cd PythonAgent
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
pip install --upgrade pip
pip install -r requirements.txt
```

Файл `requirements.txt` содержит:

```txt
flask==3.0.0
anthropic==0.39.0
python-dotenv==1.0.0
gunicorn==21.2.0
httpx==0.27.2
httpcore==1.0.2
```

### 1.3. Настройка переменных окружения

Создайте локальный файл `.env` в корне проекта:

```env
ANTHROPIC_API_KEY=your_key_here
PORT=3000
```

> **Важно:** `.env` не должен попадать в git. Убедитесь, что он добавлен в `.gitignore`.

### 1.4. Запуск локально (dev-сервер Flask)

```bash
source venv/bin/activate
python App.py
```

Приложение поднимется на порту `3000`:

- http://127.0.0.1:3000
- http://localhost:3000

Проверка health:

```bash
curl http://127.0.0.1:3000/health
# ожидается: {"status": "ok"}
```

---

## 2. Настройка VPS-сервера (Hetzner, Ubuntu)

Пример конфигурации:
- Ubuntu 24.04 LTS;
- пользователь: `agent`;
- IP-адреса сервера:
  - IPv4: `95.217.187.167`
  - IPv6: `2a01:4f9:c012:a888::1`

### 2.1. Логин на сервер по SSH

С локальной машины (Mac):

```bash
ssh agent@95.217.187.167
# или по IPv6
ssh agent@2a01:4f9:c012:a888::1
```

При первом подключении SSH спросит про fingerprint — отвечаем `yes`.

Если менялся сервер/ключ и SSH ругается, можно удалить старые записи:

```bash
ssh-keygen -R 95.217.187.167
ssh-keygen -R 2a01:4f9:c012:a888::1
```

### 2.2. Базовая настройка Python на сервере

На VPS (под `agent`):

```bash
sudo apt update
sudo apt install -y python3 python3-pip python3.12-venv git
```

---

## 3. Деплой проекта на сервер

Есть два основных варианта: через `scp` или через `git`.

### 3.1. Вариант A: деплой через `scp` с локальной машины

На локальной машине (Mac), из папки с проектами:

```bash
cd /Users/anton/IdeaProjects
scp -r PythonAgent agent@95.217.187.167:~/
```

После этого на сервере проект будет в `/home/agent/PythonAgent`.

### 3.2. Вариант B: деплой через git (рекомендуется)

1. Заливаем код в GitHub (репозиторий `PythonAgent`).
2. На сервере:

```bash
ssh agent@95.217.187.167
cd ~
git clone https://github.com/YOUR_LOGIN/YOUR_REPO.git PythonAgent
```

Если проект уже был, можно вместо этого делать:

```bash
cd ~/PythonAgent
git pull
```

Файл `.env` на сервере всегда создаётся/обновляется вручную и в репозиторий не коммитится.

---

## 4. Настройка окружения на сервере

На сервере:

```bash
ssh agent@95.217.187.167
cd ~/PythonAgent
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

Создайте `.env` на сервере (ключ можно другой, чем локально):

```bash
cd ~/PythonAgent
nano .env
```

Содержимое, например:

```env
ANTHROPIC_API_KEY=your_production_key_here
PORT=3000
```

> `.env` остаётся только на сервере, в git его не добавляем.

Проверка приложения на сервере (dev-режим):

```bash
source venv/bin/activate
python App.py
```

Из другой SSH-сессии или с сервера:

```bash
curl http://127.0.0.1:3000/health
```

Извне (с локальной машины):

```bash
curl http://95.217.187.167:3000/health
```

---

## 5. Продакшн-запуск через gunicorn

Для продакшна вместо `python App.py` используем gunicorn.

### 5.1. Ручной запуск gunicorn

На сервере:

```bash
cd ~/PythonAgent
source venv/bin/activate
gunicorn -w 4 -b 0.0.0.0:8000 App:app
```

- `-w 4` — число воркеров;
- `-b 0.0.0.0:8000` — слушать на всех интерфейсах порт `8000`;
- `App:app` — файл `App.py` и объект Flask-приложения `app`.

Проверка:

```bash
curl http://127.0.0.1:8000/health
```

Из браузера на локальной машине:

```text
http://95.217.187.167:8000
```

> При ручном запуске gunicorn в этой консоли процесс завершится при `Ctrl+C` или закрытии SSH.

---

## 6. Автоматический запуск через systemd

Чтобы приложение работало, даже когда вы выходите из SSH или выключаете локальный компьютер, на VPS создаётся systemd-сервис.

### 6.1. Создание сервиса

На сервере (один раз):

```bash
sudo nano /etc/systemd/system/pythonagent.service
```

Содержимое файла:

```ini
[Unit]
Description=PythonAgent Gunicorn Service
After=network.target

[Service]
User=agent
Group=agent
WorkingDirectory=/home/agent/PythonAgent
Environment=PYTHONUNBUFFERED=1
ExecStart=/home/agent/PythonAgent/venv/bin/gunicorn -w 4 -b 0.0.0.0:8000 App:app
Restart=always

[Install]
WantedBy=multi-user.target
```

Сохранить и выйти.

### 6.2. Активация и запуск сервиса

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now pythonagent.service
```

Проверка статуса:

```bash
systemctl status pythonagent.service
```

Ожидаем `Active: active (running)`.

Теперь сервер сам поднимает приложение при загрузке, и оно не зависит от SSH-сессии.

---

## 7. Деплой новой версии

### 7.1. Обновление кода на сервере (вариант с git)

```bash
ssh agent@95.217.187.167
cd ~/PythonAgent
git pull
source venv/bin/activate
pip install -r requirements.txt  # если изменился requirements.txt
sudo systemctl restart pythonagent.service
```

### 7.2. Обновление кода на сервере (вариант с scp)

На локальной машине:

```bash
cd /Users/anton/IdeaProjects
scp -r PythonAgent agent@95.217.187.167:~/
```

Затем на сервере:

```bash
ssh agent@95.217.187.167
cd ~/PythonAgent
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart pythonagent.service
```

> После деплоя **надо перезапустить сервис**:
>
> ```bash
> sudo systemctl restart pythonagent.service
> ```

---

## 8. Полезные команды

### SSH и навигация

```bash
ssh agent@95.217.187.167   # вход на сервер
cd ~/PythonAgent           # перейти в проект
source venv/bin/activate   # активировать venv
```

### Проверка сервиса и логов

```bash
systemctl status pythonagent.service
sudo journalctl -u pythonagent.service -n 50 -f
```

### Проверка доступности HTTP

```bash
curl http://127.0.0.1:8000/health
curl http://95.217.187.167:8000/health
```

---

Теперь README содержит все шаги по настройке окружения, сервера, логину на VPS, деплою и перезапуску сервиса.
