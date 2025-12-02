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
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> Tuple[Optional[str], Optional[Dict], int]:
        """
        Отправляет сообщение в Claude API и возвращает ответ.

        Args:
            user_message: Сообщение пользователя
            output_format: Формат вывода ('default', 'json', 'xml')
            model: Модель Claude для использования
            max_tokens: Максимальное количество токенов в ответе
            spec_mode: Режим сбора уточняющих данных (True/False)
            conversation_history: История диалога (список сообщений с role и content)

        Returns:
            Кортеж из (ответ, ошибка, HTTP код):
            - ответ: Текст ответа от Claude или None при ошибке
            - ошибка: Словарь с описанием ошибки или None при успехе
            - HTTP код: Код статуса HTTP
        """
        try:
            logger.info(f"Сообщение пользователя: {user_message[:MAX_MESSAGE_LOG_LENGTH]}...")
            logger.info(f"Запрошенный формат вывода: {output_format}")
            logger.info(f"Режим spec: {spec_mode}")
            logger.info(f"Max tokens: {max_tokens}")
            logger.info(f"История диалога: {len(conversation_history or [])} сообщений")

            # Валидация формата
            if not self.validate_output_format(output_format):
                logger.warning(f"Неподдерживаемый формат: {output_format}, используется default")
                output_format = OUTPUT_FORMAT_DEFAULT

            # Получаем системный промпт для выбранного формата и режима
            try:
                system_prompt = get_system_prompt(output_format, spec_mode)
            except ValueError as e:
                logger.error(f"Ошибка получения системного промпта: {str(e)}")
                return None, {'error': str(e)}, HTTP_INTERNAL_SERVER_ERROR

            # Получаем чистое сообщение пользователя
            clean_user_message = get_user_message(user_message)

            # Логируем тип запроса
            format_names = {
                'default': 'обычным форматом',
                'json': 'форматом JSON',
                'xml': 'форматом XML'
            }
            mode_str = " (spec mode)" if spec_mode else ""
            logger.info(f"Отправка запроса к Claude API с {format_names.get(output_format, 'неизвестным форматом')}{mode_str}...")
            logger.debug(f"Системный промпт: {system_prompt[:100]}...")

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
                "messages": messages
            }

            # Добавляем stop_sequences для spec mode
            if spec_mode:
                api_params["stop_sequences"] = [SPEC_END_MARKER]
                logger.debug(f"Добавлен stop_sequence: {SPEC_END_MARKER}")

            # Отправляем запрос к API
            message = self.client.messages.create(**api_params)
            
            # Извлекаем ответ
            raw_reply = message.content[0].text
            logger.info(f"Сырой ответ от Claude: {raw_reply[:MAX_REPLY_LOG_LENGTH]}...")
            
            return raw_reply, None, 200
            
        except AuthenticationError as e:
            error_msg = f"Ошибка аутентификации API: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            return None, {'error': ERROR_INVALID_API_KEY}, HTTP_INTERNAL_SERVER_ERROR
        
        except RateLimitError as e:
            error_msg = f"Превышен лимит запросов: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            return None, {'error': ERROR_RATE_LIMIT}, HTTP_TOO_MANY_REQUESTS
        
        except APIConnectionError as e:
            error_msg = f"Ошибка соединения с API: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            return None, {'error': ERROR_CONNECTION}, HTTP_SERVICE_UNAVAILABLE
        
        except APIError as e:
            error_msg = f"Ошибка Claude API: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            return None, {'error': f'Ошибка Claude API: {str(e)}'}, HTTP_INTERNAL_SERVER_ERROR
        
        except Exception as e:
            error_msg = f"Неожиданная ошибка: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            return None, {'error': f'Ошибка сервера: {str(e)}'}, HTTP_INTERNAL_SERVER_ERROR
    
    def is_api_key_configured(self) -> bool:
        return bool(self.api_key)

