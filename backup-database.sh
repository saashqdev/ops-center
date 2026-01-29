#!/bin/bash
# Database Backup Shell Script
# Wrapper script for easy database backups

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_CLI="$SCRIPT_DIR/backend/backup_cli.py"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Load environment variables from .env if it exists
if [ -f "$SCRIPT_DIR/.env" ]; then
    export $(grep -v '^#' "$SCRIPT_DIR/.env" | xargs)
fi

# Set default environment variables if not set
export POSTGRES_HOST="${POSTGRES_HOST:-postgresql}"
export POSTGRES_PORT="${POSTGRES_PORT:-5432}"
export POSTGRES_DB="${POSTGRES_DB:-unicorn_db}"
export POSTGRES_USER="${POSTGRES_USER:-unicorn}"
export POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-change-me}"
export BACKUP_DIR="${BACKUP_DIR:-/app/backups/database}"
export BACKUP_RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-7}"
export BACKUP_MAX_COUNT="${BACKUP_MAX_COUNT:-30}"

# Check if python3 is available
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python3 is not installed${NC}"
    exit 1
fi

# Check if pg_dump is available
if ! command -v pg_dump &> /dev/null; then
    echo -e "${YELLOW}⚠️  pg_dump is not installed. Installing postgresql-client...${NC}"
    
    # Try to install based on OS
    if [ -f /etc/debian_version ]; then
        apt-get update && apt-get install -y postgresql-client
    elif [ -f /etc/redhat-release ]; then
        yum install -y postgresql
    else
        echo -e "${RED}❌ Could not install postgresql-client. Please install manually.${NC}"
        exit 1
    fi
fi

# Execute the Python CLI
python3 "$BACKUP_CLI" "$@"
