# Connection settings live in backend/local-settings.json. Run from any folder.
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$pythonPath = Join-Path $projectRoot '.venv\Scripts\python.exe'
$backendPath = Join-Path $projectRoot 'backend'
if (-not (Test-Path -LiteralPath $pythonPath)) {
    throw 'The project Python environment is missing. Complete the README dependency setup first.'
}
if (Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue) {
    throw 'Port 8000 is already in use. Stop the previous backend with Ctrl+C in its terminal, then run this script again.'
}

Push-Location -LiteralPath $backendPath
try {
    $configurationCheck = @'
import sys
from pydantic import ValidationError
from app.config import settings
try:
    settings()
except (ValidationError, ValueError, TypeError):
    sys.exit('Complete database.password in backend/local-settings.json and check its format.')
'@
    & $pythonPath -c $configurationCheck
    if ($LASTEXITCODE -ne 0) { throw 'Backend configuration is incomplete. Edit the local settings file.' }
    Write-Host 'Starting the project backend at http://127.0.0.1:8000. Keep this terminal open.'
    & $pythonPath -m uvicorn app.main:app --app-dir $backendPath --host 127.0.0.1 --port 8000 --no-proxy-headers
    if ($LASTEXITCODE -ne 0) { throw 'Backend exited with an error. Review the message above.' }
} finally {
    Pop-Location
}
