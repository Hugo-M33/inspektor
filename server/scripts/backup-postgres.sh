#!/bin/bash

# PostgreSQL Backup Script for Inspektor
# Creates a compressed backup of the PostgreSQL database

set -e  # Exit on error

# Configuration
CONTAINER_NAME="${POSTGRES_CONTAINER:-inspektor-postgres-prod}"
BACKUP_DIR="${BACKUP_DIR:-/opt/inspektor/backups}"
POSTGRES_USER="${POSTGRES_USER:-inspektor}"
POSTGRES_DB="${POSTGRES_DB:-inspektor}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="inspektor_postgres_${TIMESTAMP}.sql.gz"
KEEP_BACKUPS=${KEEP_BACKUPS:-7}  # Keep last 7 backups

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Inspektor PostgreSQL Backup${NC}"
echo -e "${GREEN}========================================${NC}"
echo

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

# Check if container is running
if ! docker ps | grep -q "$CONTAINER_NAME"; then
    echo -e "${RED}Error: PostgreSQL container '$CONTAINER_NAME' is not running${NC}"
    exit 1
fi

echo -e "${YELLOW}Creating backup...${NC}"
echo "Database: $POSTGRES_DB"
echo "Container: $CONTAINER_NAME"
echo "Backup file: $BACKUP_FILE"
echo

# Create backup using pg_dump
docker exec "$CONTAINER_NAME" pg_dump \
    -U "$POSTGRES_USER" \
    -d "$POSTGRES_DB" \
    --no-owner \
    --no-acl \
    --clean \
    --if-exists \
    | gzip > "$BACKUP_DIR/$BACKUP_FILE"

if [ $? -eq 0 ]; then
    BACKUP_SIZE=$(du -h "$BACKUP_DIR/$BACKUP_FILE" | cut -f1)
    echo -e "${GREEN}✓ Backup created successfully${NC}"
    echo "  Location: $BACKUP_DIR/$BACKUP_FILE"
    echo "  Size: $BACKUP_SIZE"
    echo
else
    echo -e "${RED}✗ Backup failed${NC}"
    exit 1
fi

# Cleanup old backups
echo -e "${YELLOW}Cleaning up old backups (keeping last $KEEP_BACKUPS)...${NC}"
cd "$BACKUP_DIR"
ls -t inspektor_postgres_*.sql.gz 2>/dev/null | tail -n +$((KEEP_BACKUPS + 1)) | xargs rm -f 2>/dev/null || true

REMAINING=$(ls -1 inspektor_postgres_*.sql.gz 2>/dev/null | wc -l)
echo -e "${GREEN}✓ Cleanup complete${NC}"
echo "  Backups remaining: $REMAINING"
echo

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Backup Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
