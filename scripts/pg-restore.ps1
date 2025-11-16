Param(
  [Parameter(Mandatory=$true)][string]$InputDump,
  [string]$TargetDb = $env:POSTGRES_DB
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $InputDump)) { Write-Error "Dump file not found: $InputDump" }
if (-not $env:POSTGRES_USER -or -not $TargetDb -or -not $env:POSTGRES_PASSWORD) {
  Write-Error "POSTGRES_USER, POSTGRES_PASSWORD env vars and TargetDb are required."
}

$container = "mcp-db"
$remote = "/tmp/restore.dump"

Write-Host "Copying dump into container ..."
docker cp $InputDump "$($container):$remote"

# Create database if missing (ignore error if it already exists)
docker exec $container sh -lc "createdb -U $($env:POSTGRES_USER) $TargetDb 2>/dev/null || true"

Write-Host "Restoring into database '$TargetDb' ..."
$restoreCmd = "PGPASSWORD=$($env:POSTGRES_PASSWORD) pg_restore -U $($env:POSTGRES_USER) -d $TargetDb -1 $remote"
docker exec $container sh -lc $restoreCmd

Write-Host "Restore complete."
