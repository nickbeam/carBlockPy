"""
Database connection and models for carBlockPy application.

This module provides database connection management and data models
for users, license plates, and message history.
"""

import psycopg2
from psycopg2 import pool, sql
from psycopg2.extras import DictCursor, RealDictCursor
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from config.config_loader import load_config


# Global connection pool
_connection_pool: Optional[pool.ThreadedConnectionPool] = None


def init_connection_pool(min_connections: int = 1, max_connections: int = 10):
    """
    Initialize the database connection pool.
    
    Args:
        min_connections: Minimum number of connections in the pool.
        max_connections: Maximum number of connections in the pool.
    """
    global _connection_pool
    
    config = load_config()
    
    _connection_pool = pool.ThreadedConnectionPool(
        min_connections,
        max_connections,
        host=config.database.host,
        port=config.database.port,
        database=config.database.name,
        user=config.database.user,
        password=config.database.password
    )


def close_connection_pool():
    """Close all connections in the connection pool."""
    global _connection_pool
    
    if _connection_pool:
        _connection_pool.closeall()
        _connection_pool = None


@contextmanager
def get_db_connection():
    """
    Context manager for getting a database connection from the pool.
    
    Yields:
        psycopg2 connection object.
    """
    if _connection_pool is None:
        init_connection_pool()
    
    conn = _connection_pool.getconn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        _connection_pool.putconn(conn)


@contextmanager
def get_db_cursor(cursor_factory=DictCursor):
    """
    Context manager for getting a database cursor.
    
    Args:
        cursor_factory: The cursor factory to use.
    
    Yields:
        psycopg2 cursor object.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=cursor_factory)
        try:
            yield cursor
        finally:
            cursor.close()


# ==================== Data Models ====================

@dataclass
class User:
    """User data model."""
    id: Optional[int]
    telegram_id: int
    username: str
    registration_date: Optional[datetime] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "User":
        """Create a User instance from a dictionary."""
        return cls(
            id=data.get("id"),
            telegram_id=data["telegram_id"],
            username=data["username"],
            registration_date=data.get("registration_date")
        )


@dataclass
class LicensePlate:
    """License plate data model."""
    id: Optional[int]
    user_id: int
    plate_number: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LicensePlate":
        """Create a LicensePlate instance from a dictionary."""
        return cls(
            id=data.get("id"),
            user_id=data["user_id"],
            plate_number=data["plate_number"],
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at")
        )


@dataclass
class MessageHistory:
    """Message history data model."""
    id: Optional[int]
    sender_id: int
    recipient_id: int
    license_plate_id: int
    message_text: str
    sent_at: Optional[datetime] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MessageHistory":
        """Create a MessageHistory instance from a dictionary."""
        return cls(
            id=data.get("id"),
            sender_id=data["sender_id"],
            recipient_id=data["recipient_id"],
            license_plate_id=data["license_plate_id"],
            message_text=data["message_text"],
            sent_at=data.get("sent_at")
        )


# ==================== User Repository ====================

class UserRepository:
    """Repository for user-related database operations."""
    
    @staticmethod
    def create(telegram_id: int, username: str) -> User:
        """
        Create a new user.
        
        Args:
            telegram_id: The user's Telegram ID.
            username: The user's Telegram username.
        
        Returns:
            The created User object.
        """
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO users (telegram_id, username)
                VALUES (%s, %s)
                RETURNING *
                """,
                (telegram_id, username)
            )
            return User.from_dict(cursor.fetchone())
    
    @staticmethod
    def get_by_id(user_id: int) -> Optional[User]:
        """
        Get a user by their database ID.
        
        Args:
            user_id: The user's database ID.
        
        Returns:
            The User object or None if not found.
        """
        with get_db_cursor() as cursor:
            cursor.execute(
                "SELECT * FROM users WHERE id = %s",
                (user_id,)
            )
            result = cursor.fetchone()
            return User.from_dict(result) if result else None
    
    @staticmethod
    def get_by_telegram_id(telegram_id: int) -> Optional[User]:
        """
        Get a user by their Telegram ID.
        
        Args:
            telegram_id: The user's Telegram ID.
        
        Returns:
            The User object or None if not found.
        """
        with get_db_cursor() as cursor:
            cursor.execute(
                "SELECT * FROM users WHERE telegram_id = %s",
                (telegram_id,)
            )
            result = cursor.fetchone()
            return User.from_dict(result) if result else None
    
    @staticmethod
    def get_or_create(telegram_id: int, username: str) -> User:
        """
        Get an existing user or create a new one.
        
        Args:
            telegram_id: The user's Telegram ID.
            username: The user's Telegram username.
        
        Returns:
            The User object.
        """
        user = UserRepository.get_by_telegram_id(telegram_id)
        if user:
            return user
        return UserRepository.create(telegram_id, username)
    
    @staticmethod
    def update_username(user_id: int, username: str) -> Optional[User]:
        """
        Update a user's username.
        
        Args:
            user_id: The user's database ID.
            username: The new username.
        
        Returns:
            The updated User object or None if not found.
        """
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                UPDATE users 
                SET username = %s 
                WHERE id = %s
                RETURNING *
                """,
                (username, user_id)
            )
            result = cursor.fetchone()
            return User.from_dict(result) if result else None
    
    @staticmethod
    def delete(user_id: int) -> bool:
        """
        Delete a user.
        
        Args:
            user_id: The user's database ID.
        
        Returns:
            True if the user was deleted, False otherwise.
        """
        with get_db_cursor() as cursor:
            cursor.execute(
                "DELETE FROM users WHERE id = %s",
                (user_id,)
            )
            return cursor.rowcount > 0


# ==================== License Plate Repository ====================

class LicensePlateRepository:
    """Repository for license plate-related database operations."""
    
    @staticmethod
    def create(user_id: int, plate_number: str) -> LicensePlate:
        """
        Create a new license plate for a user.
        
        Args:
            user_id: The user's database ID.
            plate_number: The license plate number.
        
        Returns:
            The created LicensePlate object.
        
        Raises:
            psycopg2.IntegrityError: If the plate number already exists.
        """
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO license_plates (user_id, plate_number)
                VALUES (%s, %s)
                RETURNING *
                """,
                (user_id, plate_number)
            )
            return LicensePlate.from_dict(cursor.fetchone())
    
    @staticmethod
    def get_by_id(plate_id: int) -> Optional[LicensePlate]:
        """
        Get a license plate by its database ID.
        
        Args:
            plate_id: The license plate's database ID.
        
        Returns:
            The LicensePlate object or None if not found.
        """
        with get_db_cursor() as cursor:
            cursor.execute(
                "SELECT * FROM license_plates WHERE id = %s",
                (plate_id,)
            )
            result = cursor.fetchone()
            return LicensePlate.from_dict(result) if result else None
    
    @staticmethod
    def get_by_plate_number(plate_number: str) -> Optional[LicensePlate]:
        """
        Get a license plate by its number.
        
        Args:
            plate_number: The license plate number.
        
        Returns:
            The LicensePlate object or None if not found.
        """
        with get_db_cursor() as cursor:
            cursor.execute(
                "SELECT * FROM license_plates WHERE plate_number = %s",
                (plate_number,)
            )
            result = cursor.fetchone()
            return LicensePlate.from_dict(result) if result else None
    
    @staticmethod
    def get_by_user(user_id: int) -> List[LicensePlate]:
        """
        Get all license plates for a user.
        
        Args:
            user_id: The user's database ID.
        
        Returns:
            List of LicensePlate objects.
        """
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                SELECT * FROM license_plates 
                WHERE user_id = %s 
                ORDER BY created_at DESC
                """,
                (user_id,)
            )
            return [LicensePlate.from_dict(row) for row in cursor.fetchall()]
    
    @staticmethod
    def delete(plate_id: int) -> bool:
        """
        Delete a license plate.
        
        Args:
            plate_id: The license plate's database ID.
        
        Returns:
            True if the license plate was deleted, False otherwise.
        """
        with get_db_cursor() as cursor:
            cursor.execute(
                "DELETE FROM license_plates WHERE id = %s",
                (plate_id,)
            )
            return cursor.rowcount > 0
    
    @staticmethod
    def delete_by_user_and_number(user_id: int, plate_number: str) -> bool:
        """
        Delete a license plate for a specific user.
        
        Args:
            user_id: The user's database ID.
            plate_number: The license plate number.
        
        Returns:
            True if the license plate was deleted, False otherwise.
        """
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                DELETE FROM license_plates 
                WHERE user_id = %s AND plate_number = %s
                """,
                (user_id, plate_number)
            )
            return cursor.rowcount > 0


# ==================== Message History Repository ====================

class MessageHistoryRepository:
    """Repository for message history database operations."""
    
    @staticmethod
    def create(
        sender_id: int,
        recipient_id: int,
        license_plate_id: int,
        message_text: str
    ) -> MessageHistory:
        """
        Create a new message history record.
        
        Args:
            sender_id: The sender's user ID.
            recipient_id: The recipient's user ID.
            license_plate_id: The license plate ID used for the message.
            message_text: The message text.
        
        Returns:
            The created MessageHistory object.
        """
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO message_history 
                (sender_id, recipient_id, license_plate_id, message_text)
                VALUES (%s, %s, %s, %s)
                RETURNING *
                """,
                (sender_id, recipient_id, license_plate_id, message_text)
            )
            return MessageHistory.from_dict(cursor.fetchone())
    
    @staticmethod
    def count_messages_by_sender_in_last_hour(sender_id: int) -> int:
        """
        Count messages sent by a user in the last hour.
        
        Args:
            sender_id: The sender's user ID.
        
        Returns:
            The number of messages sent in the last hour.
        """
        one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
        
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                SELECT COUNT(*) as count
                FROM message_history
                WHERE sender_id = %s AND sent_at >= %s
                """,
                (sender_id, one_hour_ago)
            )
            result = cursor.fetchone()
            return result["count"] if result else 0
    
    @staticmethod
    def get_recent_messages_by_sender(
        sender_id: int,
        limit: int = 10
    ) -> List[MessageHistory]:
        """
        Get recent messages sent by a user.
        
        Args:
            sender_id: The sender's user ID.
            limit: Maximum number of messages to return.
        
        Returns:
            List of MessageHistory objects.
        """
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                SELECT * FROM message_history
                WHERE sender_id = %s
                ORDER BY sent_at DESC
                LIMIT %s
                """,
                (sender_id, limit)
            )
            return [MessageHistory.from_dict(row) for row in cursor.fetchall()]
    
    @staticmethod
    def get_messages_by_recipient(
        recipient_id: int,
        limit: int = 10
    ) -> List[MessageHistory]:
        """
        Get messages received by a user.
        
        Args:
            recipient_id: The recipient's user ID.
            limit: Maximum number of messages to return.
        
        Returns:
            List of MessageHistory objects.
        """
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                SELECT mh.*, lp.plate_number, u.username as sender_username
                FROM message_history mh
                JOIN license_plates lp ON mh.license_plate_id = lp.id
                JOIN users u ON mh.sender_id = u.id
                WHERE mh.recipient_id = %s
                ORDER BY mh.sent_at DESC
                LIMIT %s
                """,
                (recipient_id, limit)
            )
            return [MessageHistory.from_dict(row) for row in cursor.fetchall()]
