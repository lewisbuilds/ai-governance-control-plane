Param(
  [ValidateSet("full", "diff", "incr")]
  [string]$BackupType = "full",
  [string]$ContainerName = "mcp-pgbackrest",
  [string]$Stanza = "mcpgov"
)

$ErrorActionPreference = "Stop"

Write-Host "Starting $BackupType backup..."
Write-Host "Container: $ContainerName"
Write-Host "Stanza: $Stanza"
Write-Host "----------------------------------------"

# Perform the backup
docker exec $ContainerName pgbackrest --stanza=$Stanza --type=$BackupType backup

# Display backup info
Write-Host "----------------------------------------"
Write-Host "Backup complete! Current backup status:"
docker exec $ContainerName pgbackrest --stanza=$Stanza info

Write-Host "----------------------------------------"
Write-Host "$BackupType backup completed successfully at $(Get-Date)"
