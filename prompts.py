"""
Промпты для различных форматов вывода Claude API.

Этот модуль содержит функции для генерации промптов в зависимости
от требуемого формата вывода (default, JSON, XML).
"""

from constants import OUTPUT_FORMAT_DEFAULT, OUTPUT_FORMAT_JSON, OUTPUT_FORMAT_XML


def get_default_prompt(user_message: str) -> str:
    """
    Генерирует промпт для обычного текстового ответа.
    
    Args:
        user_message: Сообщение пользователя
        
    Returns:
        Промпт для Claude API
    """
    return f"""
Ты — умный помощник. Отвечай на вопрос пользователя кратко и по существу.

Вопрос пользователя: {user_message}
"""


def get_json_prompt(user_message: str) -> str:
    """
    Генерирует промпт для ответа в формате JSON.
    
    Args:
        user_message: Сообщение пользователя
        
    Returns:
        Промпт для Claude API с инструкциями по формату JSON
    """
    return f"""
Ты — умный помощник. Отвечай строго в формате JSON.

ТВОЙ ФОРМАТ ОТВЕТА (обязателен):

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
- Только один корректный JSON-объект.

Вопрос пользователя: {user_message}
"""


def get_xml_prompt(user_message: str) -> str:
    """
    Генерирует промпт для ответа в формате XML.
    
    Args:
        user_message: Сообщение пользователя
        
    Returns:
        Промпт для Claude API с инструкциями по формату XML
    """
    return f"""
Ты — умный помощник. Отвечай строго в формате XML.

ТВОЙ ФОРМАТ ОТВЕТА (обязателен):

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
- Используй правильную XML структуру с закрывающими тегами.

Вопрос пользователя: {user_message}
"""


def get_prompt_by_format(output_format: str, user_message: str) -> str:
    """
    Возвращает промпт в зависимости от требуемого формата вывода.
    
    Args:
        output_format: Формат вывода ('default', 'json', 'xml')
        user_message: Сообщение пользователя
        
    Returns:
        Промпт для Claude API
        
    Raises:
        ValueError: Если указан неподдерживаемый формат
    """
    if output_format == OUTPUT_FORMAT_JSON:
        return get_json_prompt(user_message)
    elif output_format == OUTPUT_FORMAT_XML:
        return get_xml_prompt(user_message)
    elif output_format == OUTPUT_FORMAT_DEFAULT:
        return get_default_prompt(user_message)
    else:
        raise ValueError(f"Неподдерживаемый формат вывода: {output_format}")

