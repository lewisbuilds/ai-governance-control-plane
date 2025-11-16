#!/bin/bash
# Perform pgBackRest backup via Docker Compose
set -e

CONTAINER_NAME="${PGBACKREST_CONTAINER:-mcp-pgbackrest}"
STANZA="${PGBACKREST_STANZA:-mcpgov}"
BACKUP_TYPE="${1:-full}"

if [[ ! "$BACKUP_TYPE" =~ ^(full|diff|incr)$ ]]; then
  echo "Error: Invalid backup type '$BACKUP_TYPE'"
  echo "Usage: $0 [full|diff|incr]"
  exit 1
fi

echo "Starting $BACKUP_TYPE backup..."
echo "Container: $CONTAINER_NAME"
echo "Stanza: $STANZA"
echo "----------------------------------------"

# Perform the backup
docker exec "$CONTAINER_NAME" pgbackrest --stanza="$STANZA" --type="$BACKUP_TYPE" backup

# Display backup info
echo "----------------------------------------"
echo "Backup complete! Current backup status:"
docker exec "$CONTAINER_NAME" pgbackrest --stanza="$STANZA" info

echo "----------------------------------------"
echo "$BACKUP_TYPE backup completed successfully at $(date)"
