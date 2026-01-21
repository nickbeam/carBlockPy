#!/usr/bin/env python3
"""
Database Initialization Script for CarBlockPy2

This script creates the necessary tables for the CarBlockPy2 application:
- users: Stores user information (Telegram ID, username, registration date)
- license_plates: Stores license plates associated with users
- message_history: Stores message sending history for rate limiting
"""

import psycopg2
from psycopg2 import sql
import os
from dotenv import load_dotenv
import sys
import traceback

# Add parent directory to path to import config
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.config_loader import load_config


def get_db_connection():
    """Create a database connection using environment variables."""
    print("Loading configuration...")
    config = load_config()
    
    print(f"Connecting to database:")
    print(f"  Host: {config.database.host}")
    print(f"  Port: {config.database.port}")
    print(f"  Database: {config.database.name}")
    print(f"  User: {config.database.user}")
    
    try:
        return psycopg2.connect(
            host=config.database.host,
            port=config.database.port,
            database=config.database.name,
            user=config.database.user,
            password=config.database.password
        )
    except psycopg2.OperationalError as e:
        print(f"\n✗ Database connection failed (OperationalError):")
        print(f"  {e}")
        raise
    except psycopg2.Error as e:
        print(f"\n✗ Database connection failed:")
        print(f"  {e}")
        raise


def create_tables():
    """Create all necessary database tables."""
    
    # SQL statements for table creation
    create_users_table = """
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        telegram_id BIGINT UNIQUE NOT NULL,
        username VARCHAR(255) NOT NULL,
        registration_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );
    """
    
    create_license_plates_table = """
    CREATE TABLE IF NOT EXISTS license_plates (
        id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        plate_number VARCHAR(50) UNIQUE NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        CONSTRAINT unique_user_plate UNIQUE (user_id, plate_number)
    );
    """
    
    create_message_history_table = """
    CREATE TABLE IF NOT EXISTS message_history (
        id SERIAL PRIMARY KEY,
        sender_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        recipient_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        license_plate_id INTEGER NOT NULL REFERENCES license_plates(id) ON DELETE CASCADE,
        message_text TEXT NOT NULL,
        sent_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        CONSTRAINT no_self_message CHECK (sender_id != recipient_id)
    );
    """
    
    # Create indexes for better performance
    create_indexes = [
        "CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON users(telegram_id);",
        "CREATE INDEX IF NOT EXISTS idx_license_plates_user_id ON license_plates(user_id);",
        "CREATE INDEX IF NOT EXISTS idx_license_plates_plate_number ON license_plates(plate_number);",
        "CREATE INDEX IF NOT EXISTS idx_message_history_sender_id ON message_history(sender_id);",
        "CREATE INDEX IF NOT EXISTS idx_message_history_recipient_id ON message_history(recipient_id);",
        "CREATE INDEX IF NOT EXISTS idx_message_history_sent_at ON message_history(sent_at);",
    ]
    
    # Function to update updated_at timestamp
    create_update_timestamp_function = """
    CREATE OR REPLACE FUNCTION update_updated_at_column()
    RETURNS TRIGGER AS $$
    BEGIN
        NEW.updated_at = CURRENT_TIMESTAMP;
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
    """
    
    # Triggers for automatic updated_at updates (only for license_plates)
    create_triggers = [
        """
        DROP TRIGGER IF EXISTS update_license_plates_updated_at ON license_plates;
        CREATE TRIGGER update_license_plates_updated_at
            BEFORE UPDATE ON license_plates
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
        """,
    ]
    
    try:
        conn = get_db_connection()
        print("✓ Database connection established")
        conn.autocommit = True
        cursor = conn.cursor()
        
        print("Creating database tables...")
        
        # Create tables
        cursor.execute(create_users_table)
        print("✓ Users table created")
        
        cursor.execute(create_license_plates_table)
        print("✓ License plates table created")
        
        cursor.execute(create_message_history_table)
        print("✓ Message history table created")
        
        # Create function for updating timestamps
        cursor.execute(create_update_timestamp_function)
        print("✓ Timestamp update function created")
        
        # Create triggers
        for trigger in create_triggers:
            cursor.execute(trigger)
        print("✓ Timestamp triggers created")
        
        # Create indexes
        for index in create_indexes:
            cursor.execute(index)
        print("✓ Indexes created")
        
        print("\n✓ All database tables and structures created successfully!")
        
        cursor.close()
        conn.close()
        
    except psycopg2.Error as e:
        print(f"\n✗ Error creating database tables: {e}")
        print(f"\nPostgreSQL Error Details:")
        print(f"  Error Code: {e.pgcode if hasattr(e, 'pgcode') else 'N/A'}")
        print(f"  Error Message: {e.pgerror if hasattr(e, 'pgerror') else str(e)}")
        print(f"\nFull traceback:")
        traceback.print_exc()
        print(f"\nTroubleshooting Tips:")
        print(f"  1. Make sure PostgreSQL is running")
        print(f"  2. Verify database credentials in .env file")
        print(f"  3. Ensure the database exists (run: createdb carblockdb)")
        print(f"  4. Check that the user has proper permissions")
        sys.exit(1)
    except FileNotFoundError as e:
        print(f"\n✗ Configuration file not found: {e}")
        print(f"\nFull traceback:")
        traceback.print_exc()
        print(f"\nTroubleshooting Tips:")
        print(f"  1. Make sure config/config.yaml exists")
        print(f"  2. Create .env file from .env.example")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {type(e).__name__}: {e}")
        print(f"\nFull traceback:")
        traceback.print_exc()
        sys.exit(1)


def drop_tables():
    """Drop all tables (use with caution!)."""
    drop_statements = [
        "DROP TABLE IF EXISTS message_history CASCADE;",
        "DROP TABLE IF EXISTS license_plates CASCADE;",
        "DROP TABLE IF EXISTS users CASCADE;",
        "DROP FUNCTION IF EXISTS update_updated_at_column();",
    ]
    
    try:
        conn = get_db_connection()
        print("✓ Database connection established")
        conn.autocommit = True
        cursor = conn.cursor()
        
        print("Dropping database tables...")
        
        for statement in drop_statements:
            cursor.execute(statement)
        
        print("✓ All tables dropped successfully!")
        
        cursor.close()
        conn.close()
        
    except psycopg2.Error as e:
        print(f"\n✗ Error dropping tables: {e}")
        print(f"  Error Code: {e.pgcode if hasattr(e, 'pgcode') else 'N/A'}")
        print(f"  Error Message: {e.pgerror if hasattr(e, 'pgerror') else str(e)}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {type(e).__name__}: {e}")
        sys.exit(1)


def show_tables():
    """Show existing tables in the database."""
    try:
        conn = get_db_connection()
        print("✓ Database connection established")
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """)
        
        tables = cursor.fetchall()
        
        print("\nExisting tables:")
        for table in tables:
            print(f"  - {table[0]}")
        
        cursor.close()
        conn.close()
        
    except psycopg2.Error as e:
        print(f"\n✗ Error listing tables: {e}")
        print(f"  Error Code: {e.pgcode if hasattr(e, 'pgcode') else 'N/A'}")
        print(f"  Error Message: {e.pgerror if hasattr(e, 'pgerror') else str(e)}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {type(e).__name__}: {e}")
        sys.exit(1)


def main():
    """Main function to run the database initialization script."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Database initialization script for CarBlockPy2"
    )
    parser.add_argument(
        "--drop",
        action="store_true",
        help="Drop all tables before creating them"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List existing tables and exit"
    )
    
    args = parser.parse_args()
    
    if args.list:
        show_tables()
        return
    
    if args.drop:
        confirm = input(
            "⚠️  WARNING: This will delete all data! "
            "Are you sure you want to drop all tables? (yes/no): "
        )
        if confirm.lower() == "yes":
            drop_tables()
        else:
            print("Operation cancelled.")
            return
    
    create_tables()


if __name__ == "__main__":
    main()
