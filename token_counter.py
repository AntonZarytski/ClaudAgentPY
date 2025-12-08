"""
Модуль для подсчёта токенов с использованием Anthropic API.

Использует метод client.messages.count_tokens() для подсчёта
количества входных токенов перед отправкой сообщения.
"""

import os
import logging
import traceback
from typing import List, Dict, Optional

from anthropic import Anthropic

from constants import CLAUDE_MODEL

# Настройка логирования
logger = logging.getLogger(__name__)


class TokenCounter:
    """Класс для подсчёта токенов с использованием Anthropic API."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Инициализирует TokenCounter.

        Args:
            api_key: API ключ Anthropic. Если не указан, берётся из переменной окружения.
        """
        logger.info("TokenCounter: Инициализация...")
        self.api_key = api_key or os.getenv('ANTHROPIC_API_KEY')
        if not self.api_key:
            logger.error("TokenCounter: ANTHROPIC_API_KEY не установлен!")
            raise ValueError("ANTHROPIC_API_KEY не установлен")

        logger.info(f"TokenCounter: API ключ найден: {self.api_key[:10]}...{self.api_key[-4:]}")
        self.client = Anthropic(api_key=self.api_key)
        logger.info("TokenCounter: Anthropic клиент создан успешно")

    def count_tokens(
        self,
        system_prompt: str,
        messages: List[Dict[str, str]],
        model: str = CLAUDE_MODEL
    ) -> int:
        """
        Подсчитывает количество входных токенов для сообщения.

        Args:
            system_prompt: Системный промпт
            messages: Массив сообщений (role, content)
            model: Модель Claude

        Returns:
            Количество входных токенов
        """
        try:
            logger.debug(f"count_tokens: model={model}")
            logger.debug(f"count_tokens: system_prompt длина={len(system_prompt)}")
            logger.debug(f"count_tokens: messages количество={len(messages)}")

            # Диагностика: проверяем версию SDK и доступные методы
            import anthropic
            logger.info(f"Anthropic SDK version: {anthropic.__version__}")
            logger.info(f"Client type: {type(self.client)}")
            logger.info(f"Messages type: {type(self.client.messages)}")
            logger.info(f"Messages methods: {[m for m in dir(self.client.messages) if not m.startswith('_')]}")

            logger.info(f"Вызов client.messages.count_tokens() для {len(messages)} сообщений...")

            result = self.client.messages.count_tokens(
                model=model,
                system=system_prompt,
                messages=messages
            )

            logger.info(f"Результат от API: {result}")
            input_tokens = result.input_tokens
            logger.info(f"Подсчитано токенов: {input_tokens}")

            return input_tokens

        except Exception as e:
            logger.error(f"=== Ошибка в count_tokens() ===")
            logger.error(f"Тип ошибки: {type(e).__name__}")
            logger.error(f"Сообщение: {str(e)}")
            logger.error(f"Traceback:\n{traceback.format_exc()}")
            raise

