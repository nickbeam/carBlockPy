# Docker Setup Guide for carBlockPy

This guide explains how to run carBlockPy Telegram Bot and PostgreSQL database using Docker and Docker Compose.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Development Environment](#development-environment)
- [Production Environment](#production-environment)
- [Configuration](#configuration)
- [Useful Commands](#useful-commands)
- [Troubleshooting](#troubleshooting)

## Prerequisites

- Docker (version 20.10 or higher)
- Docker Compose (version 2.0 or higher)
- A Telegram Bot Token from [@BotFather](https://t.me/BotFather)

## Quick Start

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd carBlockPy
   ```

2. **Create environment file:**
   ```bash
   cp .env.example .env
   ```

3. **Edit `.env` file with your configuration:**
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

## Development Environment

The development configuration (`docker-compose.yml`) includes:

- **Hot-reload**: Source code is mounted as a volume, so changes are reflected immediately
- **Debug mode**: Enabled by default
- **Exposed ports**: PostgreSQL port 5432 is exposed for external database access
- **Loose restart policy**: Containers restart only on failure

### Starting Development Environment

```bash
# Build and start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Stop and remove volumes (deletes database data!)
docker-compose down -v
```

### Development Workflow

1. Make changes to the source code
2. The bot container will automatically pick up changes (due to volume mounts)
3. To restart the bot after major changes:
   ```bash
   docker-compose restart bot
   ```

## Production Environment

The production configuration (`docker-compose.prod.yml`) includes:

- **No volume mounts**: Uses the built Docker image
- **Debug disabled**: Optimized for performance
- **Internal network**: Database port is not exposed externally
- **Strict restart policy**: Containers always restart
- **Resource limits**: CPU and memory limits configured
- **Log rotation**: Automatic log file rotation

### Starting Production Environment

```bash
# Build and start services with production configuration
docker-compose -f docker-compose.prod.yml up -d --build

# View logs
docker-compose -f docker-compose.prod.yml logs -f

# Stop services
docker-compose -f docker-compose.prod.yml down
```

### Production Deployment Checklist

- [ ] Set `DEBUG=false` in `.env`
- [ ] Use strong database password
- [ ] Keep your Telegram bot token secure
- [ ] Configure proper backup strategy for PostgreSQL volume
- [ ] Set up monitoring for container health
- [ ] Review and adjust resource limits as needed

## Configuration

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `DB_HOST` | Database host | `db` | Yes |
| `DB_PORT` | Database port | `5432` | Yes |
| `DB_NAME` | Database name | `carblockdb` | Yes |
| `DB_USER` | Database user | `carblock_user` | Yes |
| `DB_PASSWORD` | Database password | - | Yes |
| `TELEGRAM_BOT_TOKEN` | Telegram bot token | - | Yes |
| `MAX_MESSAGES_PER_HOUR` | Rate limit per user | `3` | No |
| `DEBUG` | Debug mode | `true` | No |
| `TIMEZONE` | Application timezone | `Europe/Moscow` | No |
| `SKIP_DB_INIT` | Skip database initialization | `false` | No |

### Volumes

- `postgres_data` (dev) / `postgres_data_prod` (prod): Persistent PostgreSQL data storage

### Networks

- `carblock_network`: Internal Docker network for service communication

## Useful Commands

### Container Management

```bash
# List all containers
docker-compose ps

# View real-time logs
docker-compose logs -f bot
docker-compose logs -f db

# View last 100 lines of logs
docker-compose logs --tail=100 bot

# Execute command inside container
docker-compose exec bot python -c "print('Hello')"

# Access PostgreSQL database
docker-compose exec db psql -U carblock_user -d carblockdb

# Restart specific service
docker-compose restart bot

# Rebuild and restart
docker-compose up -d --build bot
```

### Database Operations

```bash
# Initialize database manually (if skipped)
docker-compose exec bot python scripts/init_db.py

# List existing tables
docker-compose exec bot python scripts/init_db.py --list

# Drop all tables (WARNING: deletes all data!)
docker-compose exec bot python scripts/init_db.py --drop
```

### Cleanup

```bash
# Stop containers
docker-compose stop

# Stop and remove containers
docker-compose down

# Stop, remove containers, and remove volumes (deletes data!)
docker-compose down -v

# Remove all unused Docker images
docker image prune -a

# Remove all unused Docker volumes
docker volume prune
```

## Troubleshooting

### Bot cannot connect to database

**Problem:** Bot fails to start with database connection errors.

**Common Causes & Solutions:**

#### 1. Wrong DB_HOST value

**Problem:** `.env` file has `DB_HOST=localhost` instead of `DB_HOST=db`.

**Solution:** In Docker Compose, each service runs in its own container. The bot container's `localhost` refers to itself, not the database container. Change `DB_HOST` to the service name `db` in your `.env` file.

```env
# Wrong (for Docker)
DB_HOST=localhost

# Correct (for Docker)
DB_HOST=db
```

#### 2. psycopg2 module not found

**Problem:** Bot container shows `ModuleNotFoundError: No module named 'psycopg2'`.

**Solution:** Rebuild the Docker image with:
```bash
docker-compose down
docker-compose up -d --build
```

The Dockerfile now installs Python dependencies directly in the final stage to ensure all packages are available.

#### 3. Database not ready

**Problem:** Bot shows "PostgreSQL not ready yet..." messages.

**Solutions:**
1. Check if database is healthy:
   ```bash
   docker-compose ps db
   ```

2. Check database logs:
   ```bash
   docker-compose logs db
   ```

3. Verify environment variables in `.env` file match database configuration.

4. Test database connection manually:
   ```bash
   docker-compose exec bot python -c "
   import psycopg2
   import os
   from dotenv import load_dotenv
   load_dotenv()
   conn = psycopg2.connect(
       host=os.getenv('DB_HOST'),
       port=os.getenv('DB_PORT'),
       database=os.getenv('DB_NAME'),
       user=os.getenv('DB_USER'),
       password=os.getenv('DB_PASSWORD')
   )
   print('Connection successful!')
   conn.close()
   "
   ```

5. Test network connectivity:
   ```bash
   docker-compose exec bot python -c "
   import socket
   s = socket.socket()
   s.connect(('db', 5432))
   print('Network connection successful')
   s.close()
   "
   ```

### Database initialization fails

**Problem:** Tables are not created automatically.

**Solutions:**
1. Check if `SKIP_DB_INIT` is set to `false` in `.env`

2. Manually run initialization:
   ```bash
   docker-compose exec bot python scripts/init_db.py
   ```

3. Check init script logs:
   ```bash
   docker-compose logs bot | grep -i "database\|table\|init"
   ```

### Container keeps restarting

**Problem:** Bot container is in a restart loop.

**Solutions:**
1. Check container logs for errors:
   ```bash
   docker-compose logs bot
   ```

2. Check container health status:
   ```bash
   docker inspect carblockpy2-bot | grep -A 10 Health
   ```

3. Verify Telegram bot token is correct.

4. Check if there are Python syntax errors in the code.

### Changes not reflected in running container

**Problem:** Code changes are not visible in the bot.

**Solutions:**
1. For development: Ensure you're using `docker-compose.yml` (not prod)
2. Restart the bot container:
   ```bash
   docker-compose restart bot
   ```
3. Check volume mounts:
   ```bash
   docker inspect carblockpy2-bot | grep -A 10 Mounts
   ```

### Out of disk space

**Problem:** Docker operations fail due to disk space.

**Solutions:**
1. Clean up unused resources:
   ```bash
   docker system prune -a --volumes
   ```

2. Check disk usage:
   ```bash
   docker system df
   ```

3. Remove old images:
   ```bash
   docker image ls
   docker rmi <image-id>
   ```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Docker Network                          │
│  ┌──────────────────┐         ┌──────────────────┐         │
│  │  Telegram Bot    │         │   PostgreSQL 15  │         │
│  │  (Python 3.11)   │────────▶│   (Alpine)       │         │
│  │                  │         │                  │         │
│  │  - Bot Logic     │         │  - Users         │         │
│  │  - Rate Limiter  │         │  - License Plates│         │
│  │  - DB Client     │         │  - Messages      │         │
│  └──────────────────┘         └──────────────────┘         │
│         ▲                            ▲                     │
│         │                            │                     │
│  Volume Mounts                Persistent Volume             │
│  (Dev only)                  (postgres_data)               │
└─────────────────────────────────────────────────────────────┘
```

## Security Considerations

1. **Never commit `.env` file** to version control
2. **Use strong passwords** for database
3. **Keep Telegram bot token secret**
4. **In production**, don't expose database ports externally
5. **Regular backups** of PostgreSQL volume
6. **Use secrets management** for sensitive data in production
7. **Keep Docker images updated** with security patches

## Additional Resources

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [PostgreSQL Docker Image](https://hub.docker.com/_/postgres)
- [python-telegram-bot Documentation](https://docs.python-telegram-bot.org/)
