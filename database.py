
"""
Database module for storing user registrations
"""

import sqlite3
from typing import List, Dict, Optional
import logging
import os

logger = logging.getLogger(__name__)


class UserDatabase:
    """SQLite database for storing user registrations"""

    def __init__(self, db_path: str = "/app/data/users.db"):
        """
        Initialize database

        Args:
            db_path: Path to database file (persistent storage!)
        """
        # Убедимся, что директория существует
        db_dir = os.path.dirname(db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
            logger.info(f"Создана директория: {db_dir}")

        self.db_path = db_path
        logger.info(f"Используется база данных: {self.db_path}")

        self._create_tables()

    def _create_tables(self):
        """Create tables if they don't exist"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Таблица пользователей
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    username TEXT NOT NULL,
                    group_num TEXT NOT NULL,
                    registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(chat_id, user_id)
                )
            """)

            # Таблица логов (опционально)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    action TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            conn.commit()
            logger.info("✅ Таблицы БД созданы/обновлены")

    def register_user(self, chat_id: int, user_id: int, username: str, group: str) -> bool:
        """
        Register user in database

        Args:
            chat_id: Telegram chat ID
            user_id: Telegram user ID
            username: User name
            group: Electricity group (e.g., "1.1")

        Returns:
            True if successful, False otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                cursor.execute("""
                    INSERT OR REPLACE INTO users (chat_id, user_id, username, group_num)
                    VALUES (?, ?, ?, ?)
                """, (chat_id, user_id, username, group))

                conn.commit()
                logger.info(f"✅ Зареєстрован користувач: {username} ({group}) в чаті {chat_id}")
                return True

        except Exception as e:
            logger.error(f"❌ Ошибка при регистрации: {e}")
            return False

    def get_user(self, chat_id: int, user_id: int) -> Optional[Dict]:
        """
        Get user info

        Args:
            chat_id: Telegram chat ID
            user_id: Telegram user ID

        Returns:
            User dict or None
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                cursor.execute("""
                    SELECT user_id, username, group_num FROM users
                    WHERE chat_id = ? AND user_id = ?
                """, (chat_id, user_id))

                row = cursor.fetchone()
                if row:
                    return {
                        "user_id": row[0],
                        "username": row[1],
                        "group": row[2]
                    }
                return None

        except Exception as e:
            logger.error(f"❌ Ошибка при получении пользователя: {e}")
            return None

    def get_chat_users(self, chat_id: int) -> List[Dict]:
        """
        Get all users in chat

        Args:
            chat_id: Telegram chat ID

        Returns:
            List of user dicts
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                cursor.execute("""
                    SELECT user_id, username, group_num FROM users
                    WHERE chat_id = ?
                    ORDER BY registered_at ASC
                """, (chat_id,))

                rows = cursor.fetchall()
                users = []
                for row in rows:
                    users.append({
                        "user_id": row[0],
                        "username": row[1],
                        "group": row[2]
                    })

                logger.debug(f"Получено {len(users)} пользователей из чата {chat_id}")
                return users

        except Exception as e:
            logger.error(f"❌ Ошибка при получении пользователей чата: {e}")
            return []

    def delete_user(self, chat_id: int, user_id: int) -> bool:
        """
        Delete user from database

        Args:
            chat_id: Telegram chat ID
            user_id: Telegram user ID

        Returns:
            True if successful, False otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                cursor.execute("""
                    DELETE FROM users
                    WHERE chat_id = ? AND user_id = ?
                """, (chat_id, user_id))

                conn.commit()
                logger.info(f"✅ Користувач видалений з чату {chat_id}")
                return True

        except Exception as e:
            logger.error(f"❌ Ошибка при удалении пользователя: {e}")
            return False

    def get_all_chats(self) -> List[int]:
        """Get all chat IDs that have registered users"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT DISTINCT chat_id FROM users")
                rows = cursor.fetchall()
                return [row[0] for row in rows]
        except Exception as e:
            logger.error(f"❌ Ошибка при получении чатов: {e}")
            return []

    def clear_all_users(self):
        """Clear all users (use with caution!)"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM users")
                conn.commit()
                logger.warning("⚠️ Все користувачі видалені з БД!")
        except Exception as e:
            logger.error(f"❌ Ошибка при очистке БД: {e}")
