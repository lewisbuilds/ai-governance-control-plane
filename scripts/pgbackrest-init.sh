#!/bin/bash
# Initialize pgBackRest stanza for Docker Compose deployment
set -e

CONTAINER_NAME="${PGBACKREST_CONTAINER:-mcp-pgbackrest}"
STANZA="${PGBACKREST_STANZA:-mcpgov}"

echo "Initializing pgBackRest stanza: $STANZA"
echo "Container: $CONTAINER_NAME"
echo "----------------------------------------"

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL to be ready..."
until docker exec mcp-db pg_isready -U "${POSTGRES_USER:-mcp}" -d "${POSTGRES_DB:-mcpgov}"; do
  echo "PostgreSQL is not ready yet, waiting..."
  sleep 2
done

echo "PostgreSQL is ready!"

# Create the stanza
echo "Creating pgBackRest stanza..."
docker exec "$CONTAINER_NAME" pgbackrest --stanza="$STANZA" stanza-create

# Verify the stanza
echo "Verifying stanza..."
docker exec "$CONTAINER_NAME" pgbackrest --stanza="$STANZA" check

# Display stanza info
echo "Stanza information:"
docker exec "$CONTAINER_NAME" pgbackrest --stanza="$STANZA" info

echo "----------------------------------------"
echo "pgBackRest stanza initialization complete!"
