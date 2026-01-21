#!/usr/bin/env python3
"""
Main entry point for CarBlockPy2 application.

This script starts the Telegram bot for license plate management
and messaging between users.
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.bot import main as bot_main


if __name__ == "__main__":
    bot_main()
