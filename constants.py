"""
Константы приложения PythonAgent.

Этот модуль содержит все константы, используемые в приложении,
включая настройки API, конфигурацию сервера и параметры логирования.
"""

# Настройки сервера
DEFAULT_PORT = 8000
DEFAULT_HOST = '0.0.0.0'
DEBUG_MODE = False

# Настройки Claude API
CLAUDE_MODEL = "claude-sonnet-4-20250514"
MAX_TOKENS = 1024

# Форматы вывода
OUTPUT_FORMAT_DEFAULT = 'default'
OUTPUT_FORMAT_JSON = 'json'
OUTPUT_FORMAT_XML = 'xml'

VALID_OUTPUT_FORMATS = [
    OUTPUT_FORMAT_DEFAULT,
    OUTPUT_FORMAT_JSON,
    OUTPUT_FORMAT_XML
]

# Настройки логирования
LOG_FILE = 'app.log'
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_LEVEL = 'INFO'

# Пути к файлам
STATIC_FOLDER = 'public'
STATIC_URL_PATH = ''
INDEX_FILE = 'index.html'

# HTTP коды ответов
HTTP_OK = 200
HTTP_BAD_REQUEST = 400
HTTP_TOO_MANY_REQUESTS = 429
HTTP_INTERNAL_SERVER_ERROR = 500
HTTP_SERVICE_UNAVAILABLE = 503

# Сообщения об ошибках
ERROR_EMPTY_MESSAGE = 'Пустое сообщение'
ERROR_INVALID_API_KEY = 'Неверный API ключ Claude'
ERROR_RATE_LIMIT = 'Превышен лимит запросов к Claude API'
ERROR_CONNECTION = 'Не удалось подключиться к Claude API'
ERROR_API_KEY_NOT_SET = 'ANTHROPIC_API_KEY не установлен'
ERROR_API_KEY_NOT_FOUND = 'ANTHROPIC_API_KEY не найден в переменных окружения!'

# Лимиты
MAX_MESSAGE_LOG_LENGTH = 200
MAX_REPLY_LOG_LENGTH = 500

# Настройки сжатия истории
COMPRESSION_THRESHOLD = 10  # Количество сообщений, после которых происходит сжатие
COMPRESSION_KEEP_RECENT = 2  # Количество последних сообщений для сохранения без сжатия
COMPRESSION_SUMMARY_MAX_TOKENS = 150  # Максимальное количество токенов для summary

