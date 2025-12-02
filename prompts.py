"""
Промпты для различных форматов вывода Claude API.

Этот модуль содержит функции для генерации системных промптов
и пользовательских сообщений в зависимости от требуемого формата вывода.

Архитектура Claude API:
- system: Параметр для системных инструкций (роль, формат ответа)
- messages[].role="user": Сообщения пользователя (только вопросы)
- messages[].role="assistant": Ответы Claude
"""

from constants import OUTPUT_FORMAT_DEFAULT, OUTPUT_FORMAT_JSON, OUTPUT_FORMAT_XML


# Базовый системный промпт
BASE_SYSTEM_PROMPT = "Ты — умный помощник. Отвечай на вопрос пользователя кратко и по существу."


def get_system_prompt(output_format: str) -> str:
    """
    Возвращает системный промпт для Claude API.

    Системный промпт включает роль ассистента и инструкции по формату вывода.
    Передается в параметр `system` при вызове API.

    Args:
        output_format: Формат вывода ('default', 'json', 'xml')

    Returns:
        Системный промпт для Claude API

    Raises:
        ValueError: Если указан неподдерживаемый формат
    """
    if output_format == OUTPUT_FORMAT_DEFAULT:
        return BASE_SYSTEM_PROMPT

    elif output_format == OUTPUT_FORMAT_JSON:
        return f"""{BASE_SYSTEM_PROMPT}

ФОРМАТ ОТВЕТА: Отвечай строго в формате JSON.

Структура ответа:
{{
  "answer": "краткий ответ на вопрос пользователя одной-двумя фразами",
  "steps": [
    "шаг 1 объяснения",
    "шаг 2 объяснения",
    "шаг 3 объяснения"
  ]
}}

Требования:
- Никакого текста до или после JSON.
- Никаких комментариев, пояснений, Markdown.
- Только один корректный JSON-объект."""

    elif output_format == OUTPUT_FORMAT_XML:
        return f"""{BASE_SYSTEM_PROMPT}

ФОРМАТ ОТВЕТА: Отвечай строго в формате XML.

Структура ответа:
<response>
  <answer>краткий ответ на вопрос пользователя одной-двумя фразами</answer>
  <steps>
    <step>шаг 1 объяснения</step>
    <step>шаг 2 объяснения</step>
    <step>шаг 3 объяснения</step>
  </steps>
</response>

Требования:
- Никакого текста до или после XML.
- Никаких комментариев, пояснений, Markdown.
- Только один корректный XML-документ.
- Используй правильную XML структуру с закрывающими тегами."""

    else:
        raise ValueError(f"Неподдерживаемый формат вывода: {output_format}")


def get_user_message(user_message: str) -> str:
    """
    Возвращает сообщение пользователя для передачи в messages[].

    Сообщение передается без дополнительных инструкций,
    так как все инструкции находятся в системном промпте.

    Args:
        user_message: Исходное сообщение пользователя

    Returns:
        Сообщение для передачи в массив messages с role="user"
    """
    return user_message.strip()