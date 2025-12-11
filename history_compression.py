"""
Модуль для сжатия истории диалога.

Этот модуль реализует механизм автоматического сжатия истории диалога
каждые N сообщений, заменяя старые сообщения на краткий summary.
"""

import os
from typing import List, Dict, Optional
from anthropic import Anthropic

from constants import (
    CLAUDE_MODEL,
    MAX_TOKENS,
    COMPRESSION_THRESHOLD,
    COMPRESSION_KEEP_RECENT,
    COMPRESSION_SUMMARY_MAX_TOKENS
)
from logger import get_logger

logger = get_logger(__name__)


class HistoryCompressor:
    """
    Класс для сжатия истории диалога с использованием Claude API.

    Каждые COMPRESSION_THRESHOLD сообщений создаёт summary предыдущих
    сообщений и заменяет их на сжатую версию.
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Инициализирует компрессор истории.

        Args:
            api_key: API ключ Anthropic. Если None, берется из переменной окружения
        """
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")

        if not self.api_key:
            logger.error("API ключ не найден для HistoryCompressor")
            raise ValueError("ANTHROPIC_API_KEY не установлен")

        self.client = Anthropic(api_key=self.api_key)
        logger.info("HistoryCompressor инициализирован")

    def should_compress(self, history: List[Dict[str, str]]) -> bool:
        """
        Проверяет, нужно ли сжимать историю.

        Args:
            history: Список сообщений истории

        Returns:
            True если нужно сжать, False иначе
        """
        # Считаем только сообщения user и assistant
        message_count = sum(
            1 for msg in history
            if msg.get('role') in ('user', 'assistant')
        )

        should_compress = message_count >= COMPRESSION_THRESHOLD

        if should_compress:
            logger.info(f"История содержит {message_count} сообщений, требуется сжатие")

        return should_compress

    def create_summary(self, messages: List[Dict[str, str]]) -> str:
        """
        Создаёт краткое резюме истории диалога используя Claude API.

        Args:
            messages: Список сообщений для сжатия

        Returns:
            Текст summary
        """
        if not messages:
            return ""

        # Формируем промпт для создания summary
        conversation_text = self._format_conversation(messages)

        summary_prompt = f"""Создай ОЧЕНЬ краткое резюме диалога (максимум 2-3 предложения).
Укажи только ключевые темы, о которых говорили. Без деталей, без форматирования.

Диалог:
{conversation_text}

КРАТКОЕ резюме (2-3 предложения):"""

        try:
            logger.info(f"Создание summary для {len(messages)} сообщений...")

            response = self.client.messages.create(
                model=CLAUDE_MODEL,
                max_tokens=COMPRESSION_SUMMARY_MAX_TOKENS,
                temperature=0.0,  # Детерминированный вывод для summary
                messages=[{
                    "role": "user",
                    "content": summary_prompt
                }]
            )

            summary = response.content[0].text.strip()

            logger.info(f"Summary создан успешно: {len(summary)} символов")
            logger.debug(f"Summary: {summary[:200]}...")

            return summary

        except Exception as e:
            logger.error(f"Ошибка при создании summary: {str(e)}")
            # В случае ошибки возвращаем краткую версию вручную
            return self._fallback_summary(messages)

    def compress_history(
        self,
        history: List[Dict[str, str]],
        keep_recent: int = None
    ) -> List[Dict[str, str]]:
        """
        Сжимает историю диалога, заменяя старые сообщения на summary.

        Args:
            history: Полная история диалога
            keep_recent: Количество последних сообщений для сохранения без сжатия
                        (по умолчанию берётся из COMPRESSION_KEEP_RECENT)

        Returns:
            Сжатая история с summary
        """
        if keep_recent is None:
            keep_recent = COMPRESSION_KEEP_RECENT

        if not self.should_compress(history):
            logger.debug("Сжатие не требуется")
            return history

        # Фильтруем только user/assistant сообщения
        dialog_messages = [
            msg for msg in history
            if msg.get('role') in ('user', 'assistant')
        ]

        if len(dialog_messages) < keep_recent:
            logger.debug("Недостаточно сообщений для сжатия")
            return history

        # Разделяем на старые (для сжатия) и новые (для сохранения)
        messages_to_compress = dialog_messages[:-keep_recent]
        messages_to_keep = dialog_messages[-keep_recent:]

        logger.info(f"Сжатие {len(messages_to_compress)} сообщений, сохранение {len(messages_to_keep)}")

        # Создаём summary
        summary_text = self.create_summary(messages_to_compress)

        # Формируем новую историю: [summary] + [последние сообщения]
        compressed_history = [
            {
                "role": "user",
                "content": f"[Ранее обсуждали: {summary_text}]"
            }
        ]

        compressed_history.extend(messages_to_keep)

        logger.info(f"История сжата: {len(history)} -> {len(compressed_history)} сообщений")

        return compressed_history

    def _format_conversation(self, messages: List[Dict[str, str]]) -> str:
        """
        Форматирует сообщения в читаемый текст для создания summary.

        Args:
            messages: Список сообщений

        Returns:
            Отформатированный текст диалога
        """
        lines = []
        for i, msg in enumerate(messages, 1):
            role = msg.get('role', 'unknown')
            content = msg.get('content', '')

            # Ограничиваем длину каждого сообщения
            if len(content) > 500:
                content = content[:500] + "..."

            role_label = "Пользователь" if role == "user" else "Ассистент"
            lines.append(f"[{i}] {role_label}: {content}")

        return "\n\n".join(lines)

    def _fallback_summary(self, messages: List[Dict[str, str]]) -> str:
        """
        Создаёт упрощенное резюме без использования API (fallback).

        Args:
            messages: Список сообщений

        Returns:
            Упрощенное резюме
        """
        user_messages = [
            msg['content'][:50] for msg in messages  # Только первые 50 символов
            if msg.get('role') == 'user'
        ]

        if not user_messages:
            return "общие вопросы"

        # Берём максимум 3 темы
        topics = ", ".join(user_messages[:3])
        return topics

    def get_compression_stats(self, history: List[Dict[str, str]]) -> Dict[str, int]:
        """
        Возвращает статистику по истории для мониторинга.

        Args:
            history: История диалога

        Returns:
            Словарь со статистикой
        """
        dialog_messages = [
            msg for msg in history
            if msg.get('role') in ('user', 'assistant')
        ]

        total_chars = sum(len(msg.get('content', '')) for msg in dialog_messages)

        return {
            'total_messages': len(dialog_messages),
            'total_characters': total_chars,
            'needs_compression': self.should_compress(history),
            'threshold': COMPRESSION_THRESHOLD
        }
