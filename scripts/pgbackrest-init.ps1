Param(
  [string]$ContainerName = "mcp-pgbackrest",
  [string]$Stanza = "mcpgov"
)

$ErrorActionPreference = "Stop"

Write-Host "Initializing pgBackRest stanza: $Stanza"
Write-Host "Container: $ContainerName"
Write-Host "----------------------------------------"

# Wait for PostgreSQL to be ready
Write-Host "Waiting for PostgreSQL to be ready..."
$maxAttempts = 30
$attempt = 0
$pgUser = if ($env:POSTGRES_USER) { $env:POSTGRES_USER } else { "mcp" }
$pgDb = if ($env:POSTGRES_DB) { $env:POSTGRES_DB } else { "mcpgov" }

while ($attempt -lt $maxAttempts) {
  try {
    docker exec mcp-db pg_isready -U $pgUser -d $pgDb 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
      Write-Host "PostgreSQL is ready!"
      break
    }
  }
  catch {
    # Ignore errors and continue waiting
  }
  
  $attempt++
  Write-Host "PostgreSQL is not ready yet, waiting... (attempt $attempt/$maxAttempts)"
  Start-Sleep -Seconds 2
}

if ($attempt -eq $maxAttempts) {
  Write-Error "PostgreSQL did not become ready in time"
}

# Create the stanza
Write-Host "Creating pgBackRest stanza..."
docker exec $ContainerName pgbackrest --stanza=$Stanza stanza-create

# Verify the stanza
Write-Host "Verifying stanza..."
docker exec $ContainerName pgbackrest --stanza=$Stanza check

# Display stanza info
Write-Host "Stanza information:"
docker exec $ContainerName pgbackrest --stanza=$Stanza info

Write-Host "----------------------------------------"
Write-Host "pgBackRest stanza initialization complete!"
