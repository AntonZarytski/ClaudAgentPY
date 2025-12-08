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
    ERROR_EMPTY_MESSAGE,
    MAX_TOKENS
)
from logger import setup_logging, get_logger
from claude_client import ClaudeClient
from token_counter import TokenCounter
from prompts import get_system_prompt

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

    Принимает сообщение пользователя и параметры настроек,
    отправляет запрос к Claude API и возвращает ответ.

    Request JSON:
        message (str): Сообщение пользователя
        output_format (str, optional): Формат вывода ('default', 'json', 'xml')
        max_tokens (int, optional): Максимальное количество токенов (128-4096)
        spec_mode (bool, optional): Режим сбора уточняющих данных
        conversation_history (list, optional): История диалога

    Returns:
        JSON ответ с полем 'reply' или 'error' и HTTP код статуса
    """
    logger.info("Получен запрос на /api/chat")

    # Получаем и валидируем данные запроса
    data = request.get_json() or {}
    is_valid, error_message = validate_chat_request(data)

    if not is_valid:
        return jsonify({'error': error_message}), HTTP_BAD_REQUEST

    # Извлекаем параметры из запроса
    user_message = data.get('message', '')
    output_format = data.get('output_format', 'default')

    # Получаем max_tokens с валидацией диапазона
    max_tokens = data.get('max_tokens', MAX_TOKENS)
    if isinstance(max_tokens, int):
        max_tokens = max(128, min(4096, max_tokens))  # Ограничиваем диапазон
    else:
        max_tokens = MAX_TOKENS

    # Получаем spec_mode
    spec_mode = data.get('spec_mode', False)
    if not isinstance(spec_mode, bool):
        spec_mode = False

    # Получаем историю диалога
    conversation_history = data.get('conversation_history', [])
    if not isinstance(conversation_history, list):
        conversation_history = []

    # Получаем температуру
    temperature = data.get('temperature', 1.0)
    if not isinstance(temperature, (int, float)):
        temperature = 1.0
    temperature = max(0.0, min(1.0, float(temperature)))

    logger.info(f"Параметры: format={output_format}, max_tokens={max_tokens}, spec_mode={spec_mode}, history_len={len(conversation_history)}, temperature={temperature}")

    # Отправляем запрос к Claude API
    reply, error, status_code, usage = claude_client.send_message(
        user_message=user_message,
        output_format=output_format,
        max_tokens=max_tokens,
        spec_mode=spec_mode,
        conversation_history=conversation_history,
        temperature=temperature
    )

    # Возвращаем результат
    if error:
        return jsonify(error), status_code

    # Формируем ответ с информацией о токенах
    response_data = {'reply': reply}
    if usage:
        response_data['usage'] = usage

    return jsonify(response_data), HTTP_OK


@app.route('/api/count_tokens', methods=['POST'])
def count_tokens() -> Tuple[Response, int]:
    """
    Подсчитывает количество токенов для сообщения.

    Ожидает JSON с полями:
    - message: текст сообщения
    - conversation_history: история диалога (опционально)
    - output_format: формат вывода (опционально)
    - spec_mode: режим spec (опционально)

    Returns:
        JSON с количеством токенов и HTTP код
    """
    import traceback

    logger.info("=== /api/count_tokens: Начало обработки запроса ===")

    try:
        data: Dict[str, Any] = request.get_json() or {}
        logger.info(f"Полученные данные: message_len={len(data.get('message', ''))}, "
                   f"output_format={data.get('output_format')}, "
                   f"spec_mode={data.get('spec_mode')}, "
                   f"history_len={len(data.get('conversation_history', []))}")

        # Получаем сообщение
        user_message = data.get('message', '').strip()
        if not user_message:
            logger.warning("Пустое сообщение")
            return jsonify({'error': ERROR_EMPTY_MESSAGE}), HTTP_BAD_REQUEST

        # Получаем параметры
        output_format = data.get('output_format', 'default')
        spec_mode = data.get('spec_mode', False)

        # Получаем историю диалога
        conversation_history = data.get('conversation_history', [])
        if not isinstance(conversation_history, list):
            conversation_history = []

        # Формируем системный промпт
        system_prompt = get_system_prompt(output_format, spec_mode)
        logger.info(f"Используется промпт: format={output_format}, spec={spec_mode}")

        logger.info(f"Длина system_prompt: {len(system_prompt)} символов")

        # Формируем массив сообщений
        messages = []
        for msg in conversation_history:
            if msg.get('role') in ('user', 'assistant') and msg.get('content'):
                messages.append({
                    "role": msg['role'],
                    "content": msg['content']
                })
        messages.append({"role": "user", "content": user_message})

        logger.info(f"Сформировано {len(messages)} сообщений для подсчёта")

        # Подсчитываем токены
        logger.info("Создание TokenCounter...")
        token_counter = TokenCounter()

        logger.info("Вызов count_tokens()...")
        input_tokens = token_counter.count_tokens(
            system_prompt=system_prompt,
            messages=messages
        )

        logger.info(f"=== Успешно подсчитано: {input_tokens} токенов ===")
        return jsonify({'input_tokens': input_tokens}), HTTP_OK

    except Exception as e:
        logger.error(f"=== Ошибка подсчёта токенов ===")
        logger.error(f"Тип ошибки: {type(e).__name__}")
        logger.error(f"Сообщение: {str(e)}")
        logger.error(f"Traceback:\n{traceback.format_exc()}")
        return jsonify({'error': str(e)}), HTTP_INTERNAL_SERVER_ERROR


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