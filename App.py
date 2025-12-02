"""
Flask приложение для чат-бота на основе Claude API.

Это приложение предоставляет веб-интерфейс для взаимодействия с Claude AI
с поддержкой различных форматов вывода (текст, JSON, XML).
"""

import os
from datetime import datetime
from typing import Tuple, Dict, Any

from flask import Flask, request, jsonify, send_from_directory, Response
from dotenv import load_dotenv

from constants import (
    DEFAULT_PORT,
    DEFAULT_HOST,
    DEBUG_MODE,
    STATIC_FOLDER,
    STATIC_URL_PATH,
    INDEX_FILE,
    HTTP_OK,
    HTTP_BAD_REQUEST,
    HTTP_INTERNAL_SERVER_ERROR,
    ERROR_EMPTY_MESSAGE
)
from logger import setup_logging, get_logger
from claude_client import ClaudeClient

# Загрузка переменных окружения
load_dotenv()

# Настройка логирования
setup_logging()
logger = get_logger(__name__)

# Инициализация Flask приложения
app = Flask(__name__, static_folder=STATIC_FOLDER, static_url_path=STATIC_URL_PATH)

# Инициализация Claude клиента
claude_client = ClaudeClient()


@app.route('/')
def index() -> Response:
    """
    Отдает главную страницу приложения.

    Returns:
        HTML страница с интерфейсом чата
    """
    return send_from_directory(STATIC_FOLDER, INDEX_FILE)


def validate_chat_request(data: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Валидирует данные запроса к /api/chat.

    Args:
        data: Данные запроса

    Returns:
        Кортеж (валидность, сообщение об ошибке)
    """
    user_message = data.get('message', '')

    if not user_message:
        logger.warning("Получено пустое сообщение")
        return False, ERROR_EMPTY_MESSAGE

    return True, ""


@app.route('/api/chat', methods=['POST'])
def chat() -> Tuple[Response, int]:
    """
    Обрабатывает запросы к чат API.

    Принимает сообщение пользователя и формат вывода,
    отправляет запрос к Claude API и возвращает ответ.

    Request JSON:
        message (str): Сообщение пользователя
        output_format (str, optional): Формат вывода ('default', 'json', 'xml')

    Returns:
        JSON ответ с полем 'reply' или 'error' и HTTP код статуса
    """
    logger.info("Получен запрос на /api/chat")

    # Получаем и валидируем данные запроса
    data = request.get_json() or {}
    is_valid, error_message = validate_chat_request(data)

    if not is_valid:
        return jsonify({'error': error_message}), HTTP_BAD_REQUEST

    user_message = data.get('message', '')
    output_format = data.get('output_format', 'default')

    # Отправляем запрос к Claude API
    reply, error, status_code = claude_client.send_message(user_message, output_format)

    # Возвращаем результат
    if error:
        return jsonify(error), status_code

    return jsonify({'reply': reply}), HTTP_OK


@app.route('/health')
def health() -> Tuple[Response, int]:
    """
    Проверяет состояние приложения.

    Returns:
        JSON с информацией о статусе приложения и HTTP код
    """
    try:
        has_api_key = claude_client.is_api_key_configured()
        return jsonify({
            'status': 'ok',
            'timestamp': datetime.now().isoformat(),
            'api_key_configured': has_api_key
        }), HTTP_OK
    except Exception as e:
        logger.error(f"Ошибка в /health: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), HTTP_INTERNAL_SERVER_ERROR


def main() -> None:
    port = int(os.environ.get('PORT', DEFAULT_PORT))
    logger.info(f"Запуск сервера на порту {port}...")
    logger.info(f"Режим отладки: {DEBUG_MODE}")
    app.run(host=DEFAULT_HOST, port=port, debug=DEBUG_MODE)


if __name__ == '__main__':
    main()