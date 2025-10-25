#!/bin/bash

# PostgreSQL Restore Script for Inspektor
# Restores a PostgreSQL database from a backup file

set -e  # Exit on error

# Configuration
CONTAINER_NAME="${POSTGRES_CONTAINER:-inspektor-postgres-prod}"
POSTGRES_USER="${POSTGRES_USER:-inspektor}"
POSTGRES_DB="${POSTGRES_DB:-inspektor}"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if backup file is provided
if [ -z "$1" ]; then
    echo -e "${RED}Error: No backup file specified${NC}"
    echo
    echo "Usage: $0 <backup_file.sql.gz>"
    echo
    echo "Example:"
    echo "  $0 /opt/inspektor/backups/inspektor_postgres_20250125_120000.sql.gz"
    echo
    exit 1
fi

BACKUP_FILE="$1"

# Check if backup file exists
if [ ! -f "$BACKUP_FILE" ]; then
    echo -e "${RED}Error: Backup file not found: $BACKUP_FILE${NC}"
    exit 1
fi

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Inspektor PostgreSQL Restore${NC}"
echo -e "${GREEN}========================================${NC}"
echo

# Check if container is running
if ! docker ps | grep -q "$CONTAINER_NAME"; then
    echo -e "${RED}Error: PostgreSQL container '$CONTAINER_NAME' is not running${NC}"
    exit 1
fi

echo -e "${YELLOW}⚠️  WARNING: This will REPLACE all data in the database!${NC}"
echo
echo "Database: $POSTGRES_DB"
echo "Container: $CONTAINER_NAME"
echo "Backup file: $BACKUP_FILE"
echo

# Confirm restore
read -p "Are you sure you want to continue? (yes/no): " CONFIRM
if [ "$CONFIRM" != "yes" ]; then
    echo "Restore cancelled."
    exit 0
fi

echo
echo -e "${YELLOW}Restoring database...${NC}"

# Restore database
gunzip -c "$BACKUP_FILE" | docker exec -i "$CONTAINER_NAME" psql \
    -U "$POSTGRES_USER" \
    -d "$POSTGRES_DB"

if [ $? -eq 0 ]; then
    echo
    echo -e "${GREEN}✓ Database restored successfully${NC}"
    echo

    # Show table count
    echo "Verifying restore..."
    TABLE_COUNT=$(docker exec "$CONTAINER_NAME" psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';")
    echo "Tables in database: $(echo $TABLE_COUNT | tr -d ' ')"
    echo
else
    echo
    echo -e "${RED}✗ Restore failed${NC}"
    exit 1
fi

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Restore Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo
echo "Next steps:"
echo "1. Restart the application: docker compose restart inspektor-server"
echo "2. Verify the data is correct"
echo "3. Test the application"
