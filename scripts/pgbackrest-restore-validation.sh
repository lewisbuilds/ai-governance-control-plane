#!/bin/bash
# Validate pgBackRest restore capability
set -e

CONTAINER_NAME="${PGBACKREST_CONTAINER:-mcp-pgbackrest}"
STANZA="${PGBACKREST_STANZA:-mcpgov}"
RESTORE_PATH="/tmp/restore-test"

echo "Starting restore validation test..."
echo "Container: $CONTAINER_NAME"
echo "Stanza: $STANZA"
echo "Restore path: $RESTORE_PATH"
echo "----------------------------------------"

# Check if stanza is valid
echo "Checking stanza validity..."
docker exec "$CONTAINER_NAME" pgbackrest --stanza="$STANZA" info

# Create restore directory inside container
echo "Creating restore test directory..."
docker exec "$CONTAINER_NAME" mkdir -p "$RESTORE_PATH"

# Perform restore to test directory
echo "Performing test restore..."
docker exec "$CONTAINER_NAME" pgbackrest --stanza="$STANZA" --pg1-path="$RESTORE_PATH" --type=default restore

# Verify critical files exist
echo "Verifying restored files..."
if ! docker exec "$CONTAINER_NAME" test -f "$RESTORE_PATH/PG_VERSION"; then
  echo "ERROR: Restore validation failed - PG_VERSION not found"
  exit 1
fi

if ! docker exec "$CONTAINER_NAME" test -d "$RESTORE_PATH/base"; then
  echo "ERROR: Restore validation failed - base directory not found"
  exit 1
fi

# Cleanup
echo "Cleaning up test restore directory..."
docker exec "$CONTAINER_NAME" rm -rf "$RESTORE_PATH"

echo "----------------------------------------"
echo "Restore validation successful!"
echo "Test completed at $(date)"
