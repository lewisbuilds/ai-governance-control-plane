Param(
  [string]$ContainerName = "mcp-pgbackrest",
  [string]$Stanza = "mcpgov",
  [string]$RestorePath = "/tmp/restore-test"
)

$ErrorActionPreference = "Stop"

Write-Host "Starting restore validation test..."
Write-Host "Container: $ContainerName"
Write-Host "Stanza: $Stanza"
Write-Host "Restore path: $RestorePath"
Write-Host "----------------------------------------"

# Check if stanza is valid
Write-Host "Checking stanza validity..."
docker exec $ContainerName pgbackrest --stanza=$Stanza info

# Create restore directory inside container
Write-Host "Creating restore test directory..."
docker exec $ContainerName mkdir -p $RestorePath

# Perform restore to test directory
Write-Host "Performing test restore..."
docker exec $ContainerName pgbackrest --stanza=$Stanza --pg1-path=$RestorePath --type=default restore

# Verify critical files exist
Write-Host "Verifying restored files..."
$pgVersionExists = docker exec $ContainerName test -f "$RestorePath/PG_VERSION" 2>&1
if ($LASTEXITCODE -ne 0) {
  Write-Error "Restore validation failed - PG_VERSION not found"
}

$baseExists = docker exec $ContainerName test -d "$RestorePath/base" 2>&1
if ($LASTEXITCODE -ne 0) {
  Write-Error "Restore validation failed - base directory not found"
}

# Cleanup
Write-Host "Cleaning up test restore directory..."
docker exec $ContainerName rm -rf $RestorePath

Write-Host "----------------------------------------"
Write-Host "Restore validation successful!"
Write-Host "Test completed at $(Get-Date)"
