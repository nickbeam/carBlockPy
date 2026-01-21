"""
Rate limiting module for CarBlockPy2 application.

This module provides rate limiting functionality to prevent abuse
of the messaging system.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional
from src.database import MessageHistoryRepository
from config.config_loader import load_config


class RateLimiter:
    """
    Rate limiter for message sending.
    
    Prevents users from sending more than a specified number of messages
    within a given time period.
    """
    
    def __init__(self, max_messages_per_hour: Optional[int] = None):
        """
        Initialize the rate limiter.
        
        Args:
            max_messages_per_hour: Maximum messages allowed per hour.
                                 If None, loads from configuration.
        """
        if max_messages_per_hour is None:
            config = load_config()
            max_messages_per_hour = config.rate_limiting.max_messages_per_hour
        
        self.max_messages_per_hour = max_messages_per_hour
    
    def can_send_message(self, sender_id: int) -> tuple[bool, str]:
        """
        Check if a user can send a message based on rate limits.
        
        Args:
            sender_id: The sender's user ID.
        
        Returns:
            A tuple of (can_send, message) where can_send is a boolean
            and message explains the reason if can_send is False.
        """
        message_count = MessageHistoryRepository.count_messages_by_sender_in_last_hour(
            sender_id
        )
        
        if message_count >= self.max_messages_per_hour:
            remaining_time = self._get_time_until_reset(sender_id)
            return (
                False,
                f"You have reached the message limit. "
                f"Please wait {remaining_time} before sending another message."
            )
        
        return True, ""
    
    def _get_time_until_reset(self, sender_id: int) -> str:
        """
        Get the time until the rate limit resets for a user.
        
        Args:
            sender_id: The sender's user ID.
        
        Returns:
            A human-readable string representing the time until reset.
        """
        recent_messages = MessageHistoryRepository.get_recent_messages_by_sender(
            sender_id,
            limit=self.max_messages_per_hour
        )
        
        if not recent_messages:
            return "0 minutes"
        
        # Find the oldest message within the limit
        oldest_message = recent_messages[-1]
        
        if oldest_message.sent_at:
            reset_time = oldest_message.sent_at + timedelta(hours=1)
            remaining = reset_time - datetime.now(timezone.utc)
            
            if remaining.total_seconds() <= 0:
                return "0 minutes"
            
            minutes = int(remaining.total_seconds() // 60)
            seconds = int(remaining.total_seconds() % 60)
            
            if minutes > 0:
                return f"{minutes} minute{'s' if minutes != 1 else ''}"
            else:
                return f"{seconds} second{'s' if seconds != 1 else ''}"
        
        return "0 minutes"
    
    def get_remaining_messages(self, sender_id: int) -> int:
        """
        Get the number of messages a user can still send.
        
        Args:
            sender_id: The sender's user ID.
        
        Returns:
            The number of messages remaining before hitting the limit.
        """
        message_count = MessageHistoryRepository.count_messages_by_sender_in_last_hour(
            sender_id
        )
        
        return max(0, self.max_messages_per_hour - message_count)
