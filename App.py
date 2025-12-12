"""
Flask приложение для чат-бота на основе Claude API.

Это приложение предоставляет веб-интерфейс для взаимодействия с Claude AI
с поддержкой различных форматов вывода (текст, JSON, XML).
"""

import os
import json
import traceback
from datetime import datetime
from typing import Tuple, Dict, Any, List

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
from history_compression import HistoryCompressor
from database import ConversationDatabase

# Загрузка переменных окружения
load_dotenv()

# Настройка логирования
setup_logging()
logger = get_logger(__name__)

# Инициализация Flask приложения
app = Flask(__name__, static_folder=STATIC_FOLDER, static_url_path=STATIC_URL_PATH)

# Инициализация Claude клиента, компрессора истории и базы данных
claude_client = ClaudeClient()
history_compressor = HistoryCompressor()
db = ConversationDatabase()


def build_messages(conversation_history: List[Dict[str, str]], user_message: str) -> List[Dict[str, str]]:
    """
    Формирует массив сообщений из истории и нового сообщения.

    Args:
        conversation_history: История диалога
        user_message: Новое сообщение пользователя

    Returns:
        Список сообщений для API
    """
    messages = []
    for msg in conversation_history:
        if msg.get('role') in ('user', 'assistant') and msg.get('content'):
            messages.append({"role": msg['role'], "content": msg['content']})
    messages.append({"role": "user", "content": user_message})
    return messages


def validate_and_clamp(value: Any, default: Any, min_val: Any = None, max_val: Any = None, value_type: type = None) -> Any:
    """
    Валидирует и ограничивает значение в заданном диапазоне.

    Args:
        value: Значение для валидации
        default: Значение по умолчанию
        min_val: Минимальное значение
        max_val: Максимальное значение
        value_type: Ожидаемый тип значения (type или tuple типов)

    Returns:
        Валидированное значение
    """
    # Проверяем тип
    if value_type and not isinstance(value, value_type):
        return default

    # Применяем ограничения диапазона
    if min_val is not None and max_val is not None:
        clamped = max(min_val, min(max_val, value))
        # Сохраняем исходный тип (int остаётся int)
        return type(value)(clamped) if isinstance(value, (int, float)) else clamped

    return value


@app.route('/')
def index() -> Response:
    """Отдает главную страницу приложения."""
    return send_from_directory(STATIC_FOLDER, INDEX_FILE)


def validate_chat_request(data: Dict[str, Any]) -> Tuple[bool, str]:
    """Валидирует данные запроса к /api/chat."""
    if not data.get('message', '').strip():
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
        session_id (str, optional): ID сессии для сохранения истории
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

    # Извлекаем и валидируем параметры
    user_message = data.get('message', '')
    session_id = data.get('session_id')
    output_format = data.get('output_format', 'default')
    max_tokens = validate_and_clamp(data.get('max_tokens', MAX_TOKENS), MAX_TOKENS, 128, 4096, int)
    temperature = validate_and_clamp(data.get('temperature', 1.0), 1.0, 0.0, 1.0, (int, float))
    spec_mode = data.get('spec_mode', False) if isinstance(data.get('spec_mode'), bool) else False
    conversation_history = data.get('conversation_history', []) if isinstance(data.get('conversation_history'), list) else []

    logger.info(f"Параметры: format={output_format}, max_tokens={max_tokens}, spec_mode={spec_mode}, history_len={len(conversation_history)}, temperature={temperature}, session_id={session_id}")

    # Сохраняем сообщение пользователя в БД
    if session_id:
        db.save_message(session_id, 'user', user_message)

    # Сжимаем историю при необходимости
    original_history_len = len(conversation_history)
    if history_compressor.should_compress(conversation_history):
        logger.info(f"Начинаем сжатие истории ({original_history_len} сообщений)...")
        conversation_history = history_compressor.compress_history(conversation_history)
        logger.info(f"История сжата: {original_history_len} -> {len(conversation_history)} сообщений")

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

    # Сохраняем ответ ассистента в БД
    if session_id:
        db.save_message(session_id, 'assistant', reply)

    # Формируем ответ с информацией о токенах и сжатой историей
    response_data = {'reply': reply}
    if usage:
        response_data['usage'] = usage

    # Если история была сжата, возвращаем новую сжатую версию
    if len(conversation_history) != original_history_len:
        response_data['compressed_history'] = conversation_history
        response_data['compression_applied'] = True
        logger.info("Возвращаем сжатую историю в ответе")
    else:
        response_data['compression_applied'] = False

    return jsonify(response_data), HTTP_OK


@app.route('/api/count_tokens', methods=['POST'])
def count_tokens() -> Tuple[Response, int]:
    """Подсчитывает количество токенов для сообщения."""
    try:
        data = request.get_json() or {}
        user_message = data.get('message', '').strip()

        if not user_message:
            logger.warning("Пустое сообщение для подсчёта токенов")
            return jsonify({'error': ERROR_EMPTY_MESSAGE}), HTTP_BAD_REQUEST

        output_format = data.get('output_format', 'default')
        spec_mode = data.get('spec_mode', False)
        conversation_history = data.get('conversation_history', []) if isinstance(data.get('conversation_history'), list) else []

        logger.info(f"Подсчёт токенов: format={output_format}, spec={spec_mode}, history_len={len(conversation_history)}")

        # Формируем системный промпт и сообщения
        system_prompt = get_system_prompt(output_format, spec_mode)
        messages = build_messages(conversation_history, user_message)

        # Подсчитываем токены
        input_tokens = TokenCounter().count_tokens(system_prompt=system_prompt, messages=messages)

        logger.info(f"Подсчитано: {input_tokens} токенов")
        return jsonify({'input_tokens': input_tokens}), HTTP_OK

    except Exception as e:
        logger.error(f"Ошибка подсчёта токенов: {e}\n{traceback.format_exc()}")
        return jsonify({'error': str(e)}), HTTP_INTERNAL_SERVER_ERROR


@app.route('/health')
def health() -> Tuple[Response, int]:
    """Проверяет состояние приложения."""
    try:
        return jsonify({
            'status': 'ok',
            'timestamp': datetime.now().isoformat(),
            'api_key_configured': claude_client.is_api_key_configured()
        }), HTTP_OK
    except Exception as e:
        logger.error(f"Ошибка в /health: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), HTTP_INTERNAL_SERVER_ERROR


# === API endpoints для работы с сессиями ===

@app.route('/api/sessions', methods=['GET'])
def get_sessions() -> Tuple[Response, int]:
    """Возвращает список всех сессий."""
    try:
        sessions = db.get_all_sessions()
        return jsonify({'sessions': sessions}), HTTP_OK
    except Exception as e:
        logger.error(f"Ошибка получения списка сессий: {e}")
        return jsonify({'error': str(e)}), HTTP_INTERNAL_SERVER_ERROR


@app.route('/api/sessions/<session_id>', methods=['GET'])
def get_session(session_id: str) -> Tuple[Response, int]:
    """Возвращает историю конкретной сессии."""
    try:
        history = db.get_session_history(session_id)
        stats = db.get_session_stats(session_id)
        return jsonify({
            'session_id': session_id,
            'history': history,
            'stats': stats
        }), HTTP_OK
    except Exception as e:
        logger.error(f"Ошибка получения сессии {session_id}: {e}")
        return jsonify({'error': str(e)}), HTTP_INTERNAL_SERVER_ERROR


@app.route('/api/sessions', methods=['POST'])
def create_session() -> Tuple[Response, int]:
    """Создает новую сессию."""
    try:
        data = request.get_json() or {}
        session_id = data.get('session_id')
        title = data.get('title', 'Новый диалог')

        if not session_id:
            return jsonify({'error': 'session_id обязателен'}), HTTP_BAD_REQUEST

        success = db.create_session(session_id, title)
        if success:
            return jsonify({'session_id': session_id, 'title': title}), HTTP_OK
        else:
            return jsonify({'error': 'Сессия уже существует'}), HTTP_BAD_REQUEST

    except Exception as e:
        logger.error(f"Ошибка создания сессии: {e}")
        return jsonify({'error': str(e)}), HTTP_INTERNAL_SERVER_ERROR


@app.route('/api/sessions/<session_id>', methods=['DELETE'])
def delete_session(session_id: str) -> Tuple[Response, int]:
    """Удаляет сессию."""
    try:
        success = db.delete_session(session_id)
        if success:
            return jsonify({'message': 'Сессия удалена'}), HTTP_OK
        else:
            return jsonify({'error': 'Ошибка удаления'}), HTTP_INTERNAL_SERVER_ERROR
    except Exception as e:
        logger.error(f"Ошибка удаления сессии {session_id}: {e}")
        return jsonify({'error': str(e)}), HTTP_INTERNAL_SERVER_ERROR


@app.route('/api/sessions/<session_id>/export', methods=['GET'])
def export_session(session_id: str) -> Tuple[Response, int]:
    """Экспортирует сессию в JSON."""
    try:
        import tempfile

        # Создаем временный файл
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp:
            tmp_path = tmp.name

        # Экспортируем в файл
        success = db.export_to_json(session_id, tmp_path)

        if not success:
            return jsonify({'error': 'Сессия не найдена'}), HTTP_BAD_REQUEST

        # Читаем и возвращаем содержимое
        with open(tmp_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Удаляем временный файл
        os.remove(tmp_path)

        return jsonify(data), HTTP_OK

    except Exception as e:
        logger.error(f"Ошибка экспорта сессии {session_id}: {e}")
        return jsonify({'error': str(e)}), HTTP_INTERNAL_SERVER_ERROR


def main() -> None:
    port = int(os.environ.get('PORT', DEFAULT_PORT))
    logger.info(f"Запуск сервера на порту {port}...")
    logger.info(f"Режим отладки: {DEBUG_MODE}")
    app.run(host=DEFAULT_HOST, port=port, debug=DEBUG_MODE)


if __name__ == '__main__':
    main()