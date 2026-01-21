#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}CarBlockPy2 Docker Entrypoint${NC}"
echo -e "${GREEN}========================================${NC}"

# Function to wait for PostgreSQL
wait_for_db() {
    local host="${DB_HOST:-db}"
    local port="${DB_PORT:-5432}"
    local max_attempts=30
    local attempt=1

    echo -e "${YELLOW}Waiting for PostgreSQL at ${host}:${port}...${NC}"

    while [ $attempt -le $max_attempts ]; do
        if python -c "
import psycopg2
import os
import sys
try:
    conn = psycopg2.connect(
        host='${host}',
        port=${port},
        database='${DB_NAME}',
        user='${DB_USER}',
        password='${DB_PASSWORD}'
    )
    conn.close()
    sys.exit(0)
except Exception as e:
    sys.exit(1)
" 2>/dev/null; then
            echo -e "${GREEN}PostgreSQL is ready!${NC}"
            return 0
        fi
        echo -e "${YELLOW}Attempt ${attempt}/${max_attempts}: PostgreSQL not ready yet...${NC}"
        sleep 2
        attempt=$((attempt + 1))
    done

    echo -e "${RED}ERROR: PostgreSQL is not available after ${max_attempts} attempts${NC}"
    exit 1
}

# Function to check if tables exist
tables_exist() {
    local host="${DB_HOST:-db}"
    local port="${DB_PORT:-5432}"

    python -c "
import psycopg2
import os
import sys
try:
    conn = psycopg2.connect(
        host='${host}',
        port=${port},
        database='${DB_NAME}',
        user='${DB_USER}',
        password='${DB_PASSWORD}'
    )
    cursor = conn.cursor()
    cursor.execute(
        \"SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'users')\"
    )
    result = cursor.fetchone()[0]
    cursor.close()
    conn.close()
    sys.exit(0 if result else 1)
except Exception as e:
    sys.exit(1)
"
}

# Function to initialize database
init_database() {
    echo -e "${YELLOW}Initializing database tables...${NC}"
    
    if python scripts/init_db.py; then
        echo -e "${GREEN}Database initialized successfully!${NC}"
    else
        echo -e "${RED}ERROR: Failed to initialize database${NC}"
        exit 1
    fi
}

# Main execution
main() {
    # Wait for database to be ready
    wait_for_db

    # Check if we need to initialize the database
    if [ "${SKIP_DB_INIT:-false}" != "true" ]; then
        if tables_exist; then
            echo -e "${GREEN}Database tables already exist. Skipping initialization.${NC}"
        else
            init_database
        fi
    else
        echo -e "${YELLOW}Skipping database initialization (SKIP_DB_INIT=true)${NC}"
    fi

    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}Starting CarBlockPy2 Bot...${NC}"
    echo -e "${GREEN}========================================${NC}"

    # Execute the main command
    exec "$@"
}

# Run main function
main "$@"
