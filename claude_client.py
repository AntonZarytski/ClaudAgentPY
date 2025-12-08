"""
Клиент для работы с Claude API.

Этот модуль инкапсулирует логику взаимодействия с Anthropic Claude API,
включая отправку запросов и обработку ответов.
"""

import os
import traceback
from typing import Dict, Tuple, Optional, List

from anthropic import Anthropic, APIError, APIConnectionError, RateLimitError, AuthenticationError

from constants import (
    CLAUDE_MODEL,
    MAX_TOKENS,
    OUTPUT_FORMAT_DEFAULT,
    VALID_OUTPUT_FORMATS,
    MAX_MESSAGE_LOG_LENGTH,
    MAX_REPLY_LOG_LENGTH,
    ERROR_INVALID_API_KEY,
    ERROR_RATE_LIMIT,
    ERROR_CONNECTION,
    ERROR_API_KEY_NOT_SET,
    ERROR_API_KEY_NOT_FOUND,
    HTTP_TOO_MANY_REQUESTS,
    HTTP_INTERNAL_SERVER_ERROR,
    HTTP_SERVICE_UNAVAILABLE
)
from prompts import get_system_prompt, get_user_message, SPEC_END_MARKER
from logger import get_logger

logger = get_logger(__name__)


class ClaudeClient:
    """
    Клиент для взаимодействия с Claude API.
    
    Attributes:
        client: Экземпляр Anthropic клиента
        api_key: API ключ для аутентификации
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Инициализирует Claude клиент.
        
        Args:
            api_key: API ключ Anthropic. Если None, берется из переменной окружения
            
        Raises:
            ValueError: Если API ключ не найден
        """
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        
        if not self.api_key:
            logger.error(ERROR_API_KEY_NOT_FOUND)
            raise ValueError(ERROR_API_KEY_NOT_SET)
        
        logger.info(f"API ключ загружен: {self.api_key[:10]}...{self.api_key[-4:] if len(self.api_key) > 14 else ''}")
        
        try:
            self.client = Anthropic(api_key=self.api_key)
            logger.info("Anthropic клиент успешно инициализирован")
        except Exception as e:
            logger.error(f"Ошибка инициализации Anthropic клиента: {str(e)}")
            raise
    
    def validate_output_format(self, output_format: str) -> bool:
        """
        Проверяет валидность формата вывода.
        
        Args:
            output_format: Формат вывода для проверки
            
        Returns:
            True если формат валиден, False иначе
        """
        return output_format in VALID_OUTPUT_FORMATS
    
    def send_message(
        self,
        user_message: str,
        output_format: str = OUTPUT_FORMAT_DEFAULT,
        model: str = CLAUDE_MODEL,
        max_tokens: int = MAX_TOKENS,
        spec_mode: bool = False,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        temperature: float = 1.0
    ) -> Tuple[Optional[str], Optional[Dict], int, Optional[Dict]]:
        """
        Отправляет сообщение в Claude API и возвращает ответ.

        Args:
            user_message: Сообщение пользователя
            output_format: Формат вывода ('default', 'json', 'xml')
            model: Модель Claude для использования
            max_tokens: Максимальное количество токенов в ответе
            spec_mode: Режим сбора уточняющих данных (True/False)
            conversation_history: История диалога (список сообщений с role и content)
            temperature: Температура генерации (0.0 - 1.0)

        Returns:
            Кортеж из (ответ, ошибка, HTTP код, usage):
            - ответ: Текст ответа от Claude или None при ошибке
            - ошибка: Словарь с описанием ошибки или None при успехе
            - HTTP код: Код статуса HTTP
            - usage: Словарь с информацией о токенах (input_tokens, output_tokens) или None
        """
        try:
            # Валидация формата
            if not self.validate_output_format(output_format):
                logger.warning(f"Неподдерживаемый формат: {output_format}, используется default")
                output_format = OUTPUT_FORMAT_DEFAULT

            # Получаем системный промпт
            try:
                system_prompt = get_system_prompt(output_format, spec_mode)
            except ValueError as e:
                logger.error(f"Ошибка получения системного промпта: {str(e)}")
                return None, {'error': str(e)}, HTTP_INTERNAL_SERVER_ERROR, None

            # Получаем чистое сообщение пользователя
            clean_user_message = get_user_message(user_message)

            # Формируем массив сообщений с историей
            messages = []

            # Добавляем историю диалога (если есть)
            if conversation_history:
                for msg in conversation_history:
                    if msg.get('role') in ('user', 'assistant') and msg.get('content'):
                        messages.append({
                            "role": msg['role'],
                            "content": msg['content']
                        })

            # Добавляем текущее сообщение пользователя
            messages.append({
                "role": "user",
                "content": clean_user_message
            })

            # Формируем параметры запроса
            api_params = {
                "model": model,
                "max_tokens": max_tokens,
                "system": system_prompt,
                "messages": messages,
                "temperature": temperature
            }

            # Добавляем stop_sequences для spec mode
            if spec_mode: api_params["stop_sequences"] = [SPEC_END_MARKER]

            # === Детальное логирование параметров API запроса ===
            logger.info("=== Отправка запроса к Claude API ===")
            logger.info(f"Модель: {model}")
            logger.info(f"Max tokens: {max_tokens}")
            logger.info(f"Temperature: {temperature}")
            # Логируем system prompt (первые 200 символов)
            system_preview = system_prompt[:200] + "..." if len(system_prompt) > 200 else system_prompt
            logger.info(f"System prompt ({len(system_prompt)} символов): \"{system_preview}\"")

            # Логируем сообщения
            logger.info(f"Сообщения ({len(messages)} шт.):")
            for i, msg in enumerate(messages, 1):
                content = msg['content']
                content_preview = content[:100] + "..." if len(content) > 100 else content
                # Убираем переносы строк для компактности
                content_preview = content_preview.replace('\n', ' ').replace('\r', '')
                logger.info(f"  [{i}] {msg['role']} ({len(content)} символов): \"{content_preview}\"")

            if spec_mode:
                logger.info(f"Stop sequences: {api_params.get('stop_sequences', [])}")
            logger.info("=====================================")

            # Отправляем запрос к API
            message = self.client.messages.create(**api_params)

            # Извлекаем ответ
            raw_reply = message.content[0].text
            logger.info(f"Сырой ответ от Claude: {raw_reply[:MAX_REPLY_LOG_LENGTH]}...")

            # Извлекаем информацию о токенах
            usage = {
                'input_tokens': message.usage.input_tokens,
                'output_tokens': message.usage.output_tokens
            }
            logger.info(f"Использовано токенов: input={usage['input_tokens']}, output={usage['output_tokens']}")

            return raw_reply, None, 200, usage

        except AuthenticationError as e:
            error_msg = f"Ошибка аутентификации API: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            return None, {'error': ERROR_INVALID_API_KEY}, HTTP_INTERNAL_SERVER_ERROR, None

        except RateLimitError as e:
            error_msg = f"Превышен лимит запросов: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            return None, {'error': ERROR_RATE_LIMIT}, HTTP_TOO_MANY_REQUESTS, None

        except APIConnectionError as e:
            error_msg = f"Ошибка соединения с API: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            return None, {'error': ERROR_CONNECTION}, HTTP_SERVICE_UNAVAILABLE, None

        except APIError as e:
            error_msg = f"Ошибка Claude API: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            return None, {'error': f'Ошибка Claude API: {str(e)}'}, HTTP_INTERNAL_SERVER_ERROR, None

        except Exception as e:
            error_msg = f"Неожиданная ошибка: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            return None, {'error': f'Ошибка сервера: {str(e)}'}, HTTP_INTERNAL_SERVER_ERROR, None
    
    def is_api_key_configured(self) -> bool:
        return bool(self.api_key)

