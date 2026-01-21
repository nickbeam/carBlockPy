"""
Configuration loader for CarBlockPy2 application.

This module loads configuration from YAML files and environment variables.
Environment variables take precedence over YAML configuration.
"""

import os
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv
import yaml


@dataclass
class DatabaseConfig:
    """Database configuration settings."""
    host: str
    port: int
    name: str
    user: str
    password: str


@dataclass
class TelegramConfig:
    """Telegram bot configuration settings."""
    bot_token: str


@dataclass
class RateLimitingConfig:
    """Rate limiting configuration settings."""
    max_messages_per_hour: int


@dataclass
class AppConfig:
    """General application configuration settings."""
    debug: bool
    timezone: str


@dataclass
class Config:
    """Main configuration class."""
    database: DatabaseConfig
    telegram: TelegramConfig
    message_template: str
    rate_limiting: RateLimitingConfig
    app: AppConfig


def load_config(config_path: Optional[str] = None) -> Config:
    """
    Load configuration from YAML file and environment variables.
    
    Args:
        config_path: Optional path to the configuration file.
                    Defaults to 'config/config.yaml'.
    
    Returns:
        Config object with all configuration settings.
    """
    # Load environment variables from .env file
    load_dotenv()
    
    # Default config path
    if config_path is None:
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "config",
            "config.yaml"
        )
    
    # Load YAML configuration
    with open(config_path, "r", encoding="utf-8") as f:
        yaml_config = yaml.safe_load(f)
    
    # Environment variables take precedence
    db_host = os.getenv("DB_HOST", yaml_config["database"]["host"])
    db_port = int(os.getenv("DB_PORT", yaml_config["database"]["port"]))
    db_name = os.getenv("DB_NAME", yaml_config["database"]["name"])
    db_user = os.getenv("DB_USER", yaml_config["database"]["user"])
    db_password = os.getenv("DB_PASSWORD", yaml_config["database"]["password"])
    
    bot_token = os.getenv(
        "TELEGRAM_BOT_TOKEN",
        yaml_config["telegram"]["bot_token"]
    )
    
    message_template = yaml_config["message_template"]
    
    max_messages = int(
        os.getenv(
            "MAX_MESSAGES_PER_HOUR",
            yaml_config["rate_limiting"]["max_messages_per_hour"]
        )
    )
    
    debug = os.getenv("DEBUG", str(yaml_config["app"]["debug"])).lower() == "true"
    timezone = os.getenv("TIMEZONE", yaml_config["app"]["timezone"])
    
    return Config(
        database=DatabaseConfig(
            host=db_host,
            port=db_port,
            name=db_name,
            user=db_user,
            password=db_password
        ),
        telegram=TelegramConfig(bot_token=bot_token),
        message_template=message_template,
        rate_limiting=RateLimitingConfig(max_messages_per_hour=max_messages),
        app=AppConfig(debug=debug, timezone=timezone)
    )
