param(
  [switch]$Fix
)

Write-Host "==> Installing dev dependencies" -ForegroundColor Cyan
python -m pip install --upgrade pip | Out-Null
pip install -r requirements-dev.txt | Out-Null

Write-Host "==> Ruff" -ForegroundColor Cyan
ruff check .

Write-Host "==> Black" -ForegroundColor Cyan
if ($Fix) {
  black .
} else {
  black --check .
}

Write-Host "==> Pylint" -ForegroundColor Cyan
pylint services

Write-Host "==> Mypy" -ForegroundColor Cyan
mypy services scripts clients

Write-Host "==> Vulture" -ForegroundColor Cyan
# Exclude common non-source directories to avoid third-party parsing issues
vulture . scripts/vulture_whitelist.py --min-confidence 80 --exclude ".venv,wheelhouse,infra/keys,backups,__pycache__"

Write-Host "All linters completed." -ForegroundColor Green
