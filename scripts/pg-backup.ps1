Param(
  [string]$Output = $(Join-Path $(Join-Path $PSScriptRoot "..\backups") ("pg-" + (Get-Date -Format "yyyyMMdd-HHmmss") + ".dump"))
)

$ErrorActionPreference = "Stop"

# Ensure output directory exists
$outDir = Split-Path -Parent $Output
if (-not (Test-Path $outDir)) { New-Item -ItemType Directory -Path $outDir | Out-Null }

if (-not $env:POSTGRES_USER -or -not $env:POSTGRES_DB -or -not $env:POSTGRES_PASSWORD) {
  Write-Error "POSTGRES_USER, POSTGRES_DB, and POSTGRES_PASSWORD environment variables are required."
}

$container = "mcp-db"
$tmpFile = "/tmp/backup.dump"

Write-Host "Creating backup inside container $container ..."
$cmd = "PGPASSWORD=$($env:POSTGRES_PASSWORD) pg_dump -U $($env:POSTGRES_USER) -d $($env:POSTGRES_DB) -Fc -f $tmpFile"
docker exec $container sh -lc $cmd

Write-Host "Copying backup to host: $Output"
docker cp "$($container):$tmpFile" $Output

Write-Host "Backup complete: $Output"
