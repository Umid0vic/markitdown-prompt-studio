@echo off
setlocal

cd /d "%~dp0"

echo Stopping MarkItDown Prompt Studio...
echo.

powershell -NoProfile -ExecutionPolicy Bypass -Command "$connections = Get-NetTCPConnection -LocalPort 8501 -State Listen -ErrorAction SilentlyContinue; if (-not $connections) { Write-Host 'No app was found listening on port 8501.'; exit 0 }; $pids = $connections | Select-Object -ExpandProperty OwningProcess -Unique; foreach ($pidValue in $pids) { Stop-Process -Id $pidValue -Force; Write-Host ('Stopped process ' + $pidValue) }"

echo.
pause
