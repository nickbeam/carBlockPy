# CarBlockPy2

A Python Telegram bot application for managing license plates and sending messages between vehicle owners.

## Features

- ✅ User registration via Telegram
- ✅ Add, list, and delete license plates
- ✅ Send messages to other users using their license plate number
- ✅ Message templates with placeholders
- ✅ Rate limiting (configurable, default 3 messages per hour)
- ✅ PostgreSQL database storage with connection pooling
- ✅ Automatic user registration on first interaction
- ✅ Docker support for easy deployment
- ✅ Database indexes for performance optimization
- ✅ Automatic timestamp updates via triggers

## Requirements

- Python 3.11 or higher (for local development)
- PostgreSQL 12 or higher
- Telegram Bot Token (from [@BotFather](https://t.me/botfather))
- Docker and Docker Compose (optional, for containerized deployment)

## Quick Start

### Using Docker (Recommended)

The fastest way to get started is using Docker Compose:

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd carBlockPy2
   ```

2. **Create environment file:**
   ```bash
   cp .env.example .env
   ```

3. **Edit `.env` with your configuration:**
   ```env
   # Database Configuration
   DB_HOST=db
   DB_PORT=5432
   DB_NAME=carblockdb
   DB_USER=carblock_user
   DB_PASSWORD=your_secure_password_here

   # Telegram Bot Configuration
   TELEGRAM_BOT_TOKEN=your_actual_bot_token_here

   # Rate Limiting Configuration
   MAX_MESSAGES_PER_HOUR=3

   # Application Settings
   DEBUG=true
   TIMEZONE=Europe/Moscow

   # Docker Configuration
   SKIP_DB_INIT=false
   ```

4. **Start the services:**
   ```bash
   docker-compose up -d
   ```

5. **Check logs:**
   ```bash
   docker-compose logs -f bot
   ```

The database will be automatically initialized on first startup. For detailed Docker documentation, see [`DOCKER.md`](DOCKER.md:1).

### Local Installation

If you prefer to run the application locally without Docker:

#### 1. Clone the repository

```bash
git clone <repository-url>
cd carBlockPy2
```

#### 2. Create a virtual environment

```bash
python -m venv venv

# On Windows:
venv\Scripts\activate

# On Unix/macOS:
source venv/bin/activate
```

#### 3. Install dependencies

```bash
pip install -r requirements.txt
```

#### 4. Set up PostgreSQL database

**Option 1: Manual setup**

Create a new database and user using SQL:

```sql
CREATE DATABASE carblockdb;
CREATE USER carblock_user WITH PASSWORD 'your_password_here';
GRANT ALL PRIVILEGES ON DATABASE carblockdb TO carblock_user;
```

**Option 2: Using existing PostgreSQL**

If you already have PostgreSQL running, just create the database and user with the commands above.

#### 5. Configure environment variables

Copy the example environment file:

```bash
cp .env.example .env
```

Edit `.env` with your actual values:

```env
# Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_NAME=carblockdb
DB_USER=carblock_user
DB_PASSWORD=your_actual_password

# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=your_actual_bot_token

# Rate Limiting Configuration
MAX_MESSAGES_PER_HOUR=3

# Application Settings
DEBUG=true
TIMEZONE=Europe/Moscow

# Docker Configuration (not used for local deployment)
SKIP_DB_INIT=false
```

#### 6. Initialize the database

Run the database initialization script:

```bash
python scripts/init_db.py
```

This will create the following tables:
- `users` - Stores user information (Telegram ID, username, registration date)
- `license_plates` - Stores license plates associated with users
- `message_history` - Stores message sending history for rate limiting

The script also creates:
- Database indexes for performance optimization
- Automatic timestamp update triggers
- Constraints for data integrity

#### 7. Update configuration (optional)

Edit [`config/config.yaml`](config/config.yaml:1) to customize:

- Message template (supports `{licence_plate}` placeholder)
- Rate limiting settings
- Application settings

## Usage

### Start the bot

**Using Docker:**
```bash
docker-compose up -d
```

**Locally:**
```bash
python main.py
```

### Available Commands

| Command | Description |
|---------|-------------|
| `/start` | Start the bot and register your account |
| `/help` | Show help message with all commands |
| `/myplates` | List all your registered license plates |
| `/addplate` | Add a new license plate |
| `/deleteplate` | Delete a license plate |
| `/sendmsg` | Send a message to another user using their license plate |
| `/cancel` | Cancel the current operation |

### Example Workflow

1. **Start the bot:**
   ```
   /start
   ```
   This registers your account in the database.

2. **Add a license plate:**
   ```
   /addplate
   ```
   Then enter your license plate number (e.g., `ABC123`).

3. **List your plates:**
   ```
   /myplates
   ```

4. **Send a message:**
   ```
   /sendmsg
   ```
   Then enter the recipient's license plate number.

## Project Structure

```
carBlockPy2/
├── config/
│   ├── __init__.py
│   ├── config.yaml          # Configuration file
│   └── config_loader.py      # Configuration loader module
├── scripts/
│   ├── __init__.py
│   └── init_db.py           # Database initialization script
├── src/
│   ├── __init__.py
│   ├── bot.py               # Telegram bot implementation
│   ├── database.py          # Database models and repositories
│   └── rate_limiter.py      # Rate limiting module
├── .dockerignore            # Docker ignore patterns
├── .env.example             # Example environment variables
├── .gitignore               # Git ignore patterns
├── docker-compose.yml       # Docker Compose for development
├── docker-compose.prod.yml  # Docker Compose for production
├── docker-entrypoint.sh     # Docker entrypoint script
├── Dockerfile               # Multi-stage Docker image
├── DOCKER.md                # Detailed Docker documentation
├── main.py                  # Application entry point
├── requirements.txt         # Python dependencies
└── README.md               # This file
```

## Database Schema

### Users Table

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL | Primary key |
| telegram_id | BIGINT | Unique Telegram user ID |
| username | VARCHAR(255) | Telegram username |
| registration_date | TIMESTAMP WITH TIME ZONE | Registration date |

### License Plates Table

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL | Primary key |
| user_id | INTEGER | Foreign key to users |
| plate_number | VARCHAR(50) | License plate number (unique) |
| created_at | TIMESTAMP WITH TIME ZONE | Record creation time |
| updated_at | TIMESTAMP WITH TIME ZONE | Last update time (auto-updated) |

**Constraints:**
- `unique_user_plate`: Ensures a user cannot register the same plate twice
- Foreign key with CASCADE delete on user deletion

### Message History Table

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL | Primary key |
| sender_id | INTEGER | Foreign key to users (sender) |
| recipient_id | INTEGER | Foreign key to users (recipient) |
| license_plate_id | INTEGER | Foreign key to license_plates |
| message_text | TEXT | Message content |
| sent_at | TIMESTAMP WITH TIME ZONE | Message send time |

**Constraints:**
- `no_self_message`: Prevents users from sending messages to themselves
- Foreign keys with CASCADE delete on user/plate deletion

### Database Indexes

The following indexes are created for performance:
- `idx_users_telegram_id` on users(telegram_id)
- `idx_license_plates_user_id` on license_plates(user_id)
- `idx_license_plates_plate_number` on license_plates(plate_number)
- `idx_message_history_sender_id` on message_history(sender_id)
- `idx_message_history_recipient_id` on message_history(recipient_id)
- `idx_message_history_sent_at` on message_history(sent_at)

## Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `DB_HOST` | Database host | `localhost` (local) / `db` (Docker) | Yes |
| `DB_PORT` | Database port | `5432` | Yes |
| `DB_NAME` | Database name | `carblockdb` | Yes |
| `DB_USER` | Database user | `carblock_user` | Yes |
| `DB_PASSWORD` | Database password | - | Yes |
| `TELEGRAM_BOT_TOKEN` | Telegram bot token | - | Yes |
| `MAX_MESSAGES_PER_HOUR` | Rate limit per user | `3` | No |
| `DEBUG` | Debug mode | `true` | No |
| `TIMEZONE` | Application timezone | `Europe/Moscow` | No |
| `SKIP_DB_INIT` | Skip database initialization (Docker) | `false` | No |

## Rate Limiting

The application implements rate limiting to prevent spam:

- Maximum 3 messages per hour per user (configurable)
- Time remaining is shown when sending messages
- Rate limit resets 1 hour after the first message in the window
- Uses database-based tracking for reliability

## Docker Deployment

The project includes comprehensive Docker support for both development and production environments.

### Development Environment

Features:
- Hot-reload via volume mounts
- Debug mode enabled
- Exposed PostgreSQL port for external access
- Loose restart policy

```bash
# Start development environment
docker-compose up -d

# View logs
docker-compose logs -f bot

# Stop services
docker-compose down
```

### Production Environment

Features:
- No volume mounts (uses built image)
- Debug disabled
- Internal network only (database not exposed)
- Strict restart policy (always restart)
- Resource limits (CPU: 0.5, Memory: 512M)
- Log rotation (10MB max, 3 files)

```bash
# Start production environment
docker-compose -f docker-compose.prod.yml up -d --build

# View logs
docker-compose -f docker-compose.prod.yml logs -f

# Stop services
docker-compose -f docker-compose.prod.yml down
```

For detailed Docker documentation including troubleshooting, see [`DOCKER.md`](DOCKER.md:1).

## Database Management

### Initialize Database

```bash
# Locally
python scripts/init_db.py

# In Docker (manual)
docker-compose exec bot python scripts/init_db.py
```

### List Existing Tables

```bash
# Locally
python scripts/init_db.py --list

# In Docker
docker-compose exec bot python scripts/init_db.py --list
```

### Drop All Tables (⚠️ Destructive)

```bash
# Locally
python scripts/init_db.py --drop

# In Docker
docker-compose exec bot python scripts/init_db.py --drop
```

### Access PostgreSQL Database

```bash
# In Docker
docker-compose exec db psql -U carblock_user -d carblockdb
```

## Security Considerations

- Never commit `.env` file to version control
- Use strong passwords for database
- Keep your Telegram bot token secure
- Consider using environment variables for all sensitive data
- In production, don't expose database ports externally
- Use secrets management for sensitive data in production
- Keep Docker images updated with security patches

## Troubleshooting

### Database connection errors

- Verify PostgreSQL is running
- Check database credentials in `.env`
- Ensure database exists and user has proper permissions
- For Docker: Ensure `DB_HOST=db` (not `localhost`)

### Bot not responding

- Verify bot token is correct
- Check that bot has been started with `/start` command
- Review logs for error messages
- Check container health status (Docker)

### Rate limiting issues

- Check `MAX_MESSAGES_PER_HOUR` in `.env` or config
- Verify message history table is properly created

### Docker issues

- Check container logs: `docker-compose logs bot`
- Verify network connectivity between containers
- Ensure environment variables are properly set
- See [`DOCKER.md`](DOCKER.md:219) for detailed troubleshooting

## Development

### Running tests (if available)

```bash
pytest tests/
```

### Code style

This project follows PEP 8 style guidelines. Use `black` for code formatting:

```bash
black src/ scripts/ main.py
```

## Architecture

### Database Connection Pooling

The application uses `psycopg2.ThreadedConnectionPool` for efficient database connection management:
- Minimum connections: 1
- Maximum connections: 10
- Automatic connection cleanup

### Automatic Timestamp Updates

The `license_plates` table has a trigger that automatically updates the `updated_at` column on any row modification.

### Data Integrity Constraints

- Unique constraint on `telegram_id` in users table
- Unique constraint on `plate_number` in license_plates table
- Composite unique constraint on `(user_id, plate_number)` to prevent duplicate plates per user
- Check constraint to prevent self-messaging

## License

This project is provided as-is for educational purposes.

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## Additional Documentation

- [`DOCKER.md`](DOCKER.md:1) - Comprehensive Docker setup and troubleshooting guide
