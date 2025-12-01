import os
import logging
import traceback
from datetime import datetime

from flask import Flask, request, jsonify, send_from_directory
from anthropic import Anthropic, APIError, APIConnectionError, RateLimitError, AuthenticationError
from dotenv import load_dotenv

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

load_dotenv()

app = Flask(__name__, static_folder='public', static_url_path='')

# Проверка наличия API ключа
api_key = os.environ.get("ANTHROPIC_API_KEY")
if not api_key:
    logger.error("ANTHROPIC_API_KEY не найден в переменных окружения!")
    raise ValueError("ANTHROPIC_API_KEY не установлен")

logger.info(f"API ключ загружен: {api_key[:10]}...{api_key[-4:] if len(api_key) > 14 else ''}")

try:
    client = Anthropic(api_key=api_key)
    logger.info("Anthropic клиент успешно инициализирован")
except Exception as e:
    logger.error(f"Ошибка инициализации Anthropic клиента: {str(e)}")
    raise

@app.route('/')
def index():
    return send_from_directory('public', 'index.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        logger.info("Получен запрос на /api/chat")
        data = request.get_json()
        user_message = data.get('message', '')

        logger.info(f"Сообщение пользователя: {user_message[:100]}...")

        if not user_message:
            logger.warning("Получено пустое сообщение")
            return jsonify({'error': 'Пустое сообщение'}), 400

        logger.info("Отправка запроса к Claude API...")
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            messages=[
                {"role": "user", "content": user_message}
            ]
        )

        reply = message.content[0].text
        logger.info(f"Получен ответ от Claude: {reply[:100]}...")
        return jsonify({'reply': reply})

    except AuthenticationError as e:
        error_msg = f"Ошибка аутентификации API: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        return jsonify({'error': 'Неверный API ключ Claude'}), 500

    except RateLimitError as e:
        error_msg = f"Превышен лимит запросов: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        return jsonify({'error': 'Превышен лимит запросов к Claude API'}), 429

    except APIConnectionError as e:
        error_msg = f"Ошибка соединения с API: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        return jsonify({'error': 'Не удалось подключиться к Claude API'}), 503

    except APIError as e:
        error_msg = f"Ошибка Claude API: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        return jsonify({'error': f'Ошибка Claude API: {str(e)}'}), 500

    except Exception as e:
        error_msg = f"Неожиданная ошибка: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        return jsonify({'error': f'Ошибка сервера: {str(e)}'}), 500

@app.route('/health')
def health():
    """Проверка здоровья сервера"""
    try:
        # Проверяем наличие API ключа
        has_api_key = bool(os.environ.get("ANTHROPIC_API_KEY"))

        return jsonify({
            'status': 'ok',
            'timestamp': datetime.now().isoformat(),
            'api_key_configured': has_api_key
        })
    except Exception as e:
        logger.error(f"Ошибка в /health: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    logger.info(f"Запуск сервера на порту {port}...")
    logger.info(f"Режим отладки: False")
    app.run(host='0.0.0.0', port=port, debug=False)