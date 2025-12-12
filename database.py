"""
Модуль для работы с базой данных SQLite для сохранения истории диалогов.

Этот модуль реализует персистентное хранилище для сообщений диалога,
позволяя сохранять и восстанавливать историю между запусками приложения.
"""

import sqlite3
import json
import os
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from contextlib import contextmanager

from logger import get_logger

logger = get_logger(__name__)

# Путь к базе данных
DB_PATH = os.path.join(os.path.dirname(__file__), 'conversations.db')


class ConversationDatabase:
    """Класс для работы с базой данных диалогов."""

    def __init__(self, db_path: str = DB_PATH):
        """
        Инициализирует базу данных.

        Args:
            db_path: Путь к файлу базы данных
        """
        self.db_path = db_path
        logger.info(f"Инициализация базы данных: {self.db_path}")
        self._init_database()

    @contextmanager
    def _get_connection(self):
        """Контекстный менеджер для работы с соединением."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Ошибка в транзакции: {e}")
            raise
        finally:
            conn.close()

    def _init_database(self):
        """Создает таблицы базы данных если их нет."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Таблица сессий
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    title TEXT,
                    created_at TEXT NOT NULL,
                    last_updated TEXT NOT NULL
                )
            ''')

            # Таблица сообщений
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
                )
            ''')

            # Индекс для быстрого поиска по session_id
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_messages_session
                ON messages(session_id)
            ''')

            logger.info("База данных инициализирована успешно")

    def create_session(self, session_id: str, title: str = "Новый диалог") -> bool:
        """
        Создает новую сессию.

        Args:
            session_id: Уникальный ID сессии
            title: Название сессии

        Returns:
            True если успешно, False при ошибке
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                now = datetime.now().isoformat()
                cursor.execute('''
                    INSERT INTO sessions (id, title, created_at, last_updated)
                    VALUES (?, ?, ?, ?)
                ''', (session_id, title, now, now))

            logger.info(f"Создана новая сессия: {session_id}")
            return True

        except sqlite3.IntegrityError:
            logger.warning(f"Сессия {session_id} уже существует")
            return False
        except Exception as e:
            logger.error(f"Ошибка создания сессии: {e}")
            return False

    def save_message(
        self,
        session_id: str,
        role: str,
        content: str
    ) -> bool:
        """
        Сохраняет сообщение в базу данных.

        Args:
            session_id: ID сессии
            role: Роль отправителя ('user' или 'assistant')
            content: Текст сообщения

        Returns:
            True если успешно, False при ошибке
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                now = datetime.now().isoformat()

                # Сохраняем сообщение
                cursor.execute('''
                    INSERT INTO messages (session_id, role, content, timestamp)
                    VALUES (?, ?, ?, ?)
                ''', (session_id, role, content, now))

                # Обновляем last_updated у сессии
                cursor.execute('''
                    UPDATE sessions
                    SET last_updated = ?
                    WHERE id = ?
                ''', (now, session_id))

            logger.debug(f"Сообщение сохранено: session={session_id}, role={role}")
            return True

        except Exception as e:
            logger.error(f"Ошибка сохранения сообщения: {e}")
            return False

    def get_session_history(
        self,
        session_id: str,
        limit: Optional[int] = None
    ) -> List[Dict[str, str]]:
        """
        Получает историю диалога для сессии.

        Args:
            session_id: ID сессии
            limit: Максимальное количество сообщений (None = все)

        Returns:
            Список сообщений в формате [{"role": "user", "content": "..."}]
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                query = '''
                    SELECT role, content
                    FROM messages
                    WHERE session_id = ?
                    ORDER BY timestamp ASC
                '''
                params = [session_id]

                if limit is not None:
                    query += ' LIMIT ?'
                    params.append(limit)

                cursor.execute(query, params)
                rows = cursor.fetchall()

                history = [
                    {"role": row["role"], "content": row["content"]}
                    for row in rows
                ]

                logger.info(f"Загружена история: session={session_id}, messages={len(history)}")
                return history

        except Exception as e:
            logger.error(f"Ошибка загрузки истории: {e}")
            return []

    def get_all_sessions(self) -> List[Dict[str, str]]:
        """
        Получает список всех сессий.

        Returns:
            Список сессий с их метаданными
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, title, created_at, last_updated
                    FROM sessions
                    ORDER BY last_updated DESC
                ''')
                rows = cursor.fetchall()

                sessions = [
                    {
                        "id": row["id"],
                        "title": row["title"],
                        "created_at": row["created_at"],
                        "last_updated": row["last_updated"]
                    }
                    for row in rows
                ]

                logger.info(f"Найдено сессий: {len(sessions)}")
                return sessions

        except Exception as e:
            logger.error(f"Ошибка получения списка сессий: {e}")
            return []

    def delete_session(self, session_id: str) -> bool:
        """
        Удаляет сессию и все её сообщения.

        Args:
            session_id: ID сессии для удаления

        Returns:
            True если успешно, False при ошибке
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                # Удаляем сессию (сообщения удалятся автоматически по CASCADE)
                cursor.execute('DELETE FROM sessions WHERE id = ?', (session_id,))

                logger.info(f"Сессия удалена: {session_id}")
                return True

        except Exception as e:
            logger.error(f"Ошибка удаления сессии: {e}")
            return False

    def clear_all_sessions(self) -> bool:
        """
        Удаляет все сессии и сообщения.

        Returns:
            True если успешно, False при ошибке
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM messages')
                cursor.execute('DELETE FROM sessions')

            logger.info("Все сессии очищены")
            return True

        except Exception as e:
            logger.error(f"Ошибка очистки всех сессий: {e}")
            return False

    def get_session_stats(self, session_id: str) -> Dict[str, int]:
        """
        Получает статистику по сессии.

        Args:
            session_id: ID сессии

        Returns:
            Словарь со статистикой
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    SELECT
                        COUNT(*) as total_messages,
                        SUM(CASE WHEN role = 'user' THEN 1 ELSE 0 END) as user_messages,
                        SUM(CASE WHEN role = 'assistant' THEN 1 ELSE 0 END) as assistant_messages
                    FROM messages
                    WHERE session_id = ?
                ''', (session_id,))

                row = cursor.fetchone()

                return {
                    "total_messages": row["total_messages"] or 0,
                    "user_messages": row["user_messages"] or 0,
                    "assistant_messages": row["assistant_messages"] or 0
                }

        except Exception as e:
            logger.error(f"Ошибка получения статистики: {e}")
            return {"total_messages": 0, "user_messages": 0, "assistant_messages": 0}

    def export_to_json(self, session_id: str, file_path: str) -> bool:
        """
        Экспортирует сессию в JSON файл.

        Args:
            session_id: ID сессии
            file_path: Путь к файлу для экспорта

        Returns:
            True если успешно, False при ошибке
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                # Получаем метаданные сессии
                cursor.execute('SELECT * FROM sessions WHERE id = ?', (session_id,))
                session_row = cursor.fetchone()

                if not session_row:
                    logger.error(f"Сессия не найдена: {session_id}")
                    return False

                # Получаем все сообщения
                cursor.execute('''
                    SELECT role, content, timestamp
                    FROM messages
                    WHERE session_id = ?
                    ORDER BY timestamp ASC
                ''', (session_id,))
                message_rows = cursor.fetchall()

                # Формируем структуру для экспорта
                export_data = {
                    "session": {
                        "id": session_row["id"],
                        "title": session_row["title"],
                        "created_at": session_row["created_at"],
                        "last_updated": session_row["last_updated"]
                    },
                    "messages": [
                        {
                            "role": row["role"],
                            "content": row["content"],
                            "timestamp": row["timestamp"]
                        }
                        for row in message_rows
                    ]
                }

                # Сохраняем в JSON
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, ensure_ascii=False, indent=2)

                logger.info(f"Сессия экспортирована в {file_path}")
                return True

        except Exception as e:
            logger.error(f"Ошибка экспорта в JSON: {e}")
            return False
