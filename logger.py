"""
Конфигурация логирования для приложения PythonAgent.

Этот модуль настраивает систему логирования с выводом в файл и консоль.
"""

import logging
from typing import Optional

from constants import LOG_FILE, LOG_FORMAT, LOG_LEVEL


def setup_logging(
    log_file: str = LOG_FILE,
    log_format: str = LOG_FORMAT,
    log_level: str = LOG_LEVEL
) -> logging.Logger:
    """
    Настраивает систему логирования приложения.
    
    Args:
        log_file: Путь к файлу логов
        log_format: Формат сообщений логов
        log_level: Уровень логирования (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        
    Returns:
        Настроенный logger объект
    """
    # Преобразуем строковый уровень в константу logging
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Настройка базовой конфигурации
    logging.basicConfig(
        level=numeric_level,
        format=log_format,
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    
    logger = logging.getLogger(__name__)
    return logger


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Возвращает logger с указанным именем.
    
    Args:
        name: Имя logger'а. Если None, используется имя модуля
        
    Returns:
        Logger объект
    """
    return logging.getLogger(name or __name__)

