@echo off
setlocal

cd /d "%~dp0"

echo Starting MarkItDown Prompt Studio...
echo.

if not exist ".venv\Scripts\python.exe" (
    echo Creating virtual environment...
    python -m venv .venv
    if errorlevel 1 (
        echo.
        echo Failed to create the virtual environment. Make sure Python is installed and available on PATH.
        pause
        exit /b 1
    )
)

set "DEPS_MARKER=.venv\.requirements-installed"
set "INSTALL_DEPS=0"

if not exist "%DEPS_MARKER%" (
    set "INSTALL_DEPS=1"
)

if "%INSTALL_DEPS%"=="0" (
    ".venv\Scripts\python.exe" -c "import fastapi, uvicorn, markitdown" >nul 2>nul
    if errorlevel 1 set "INSTALL_DEPS=1"
)

if "%INSTALL_DEPS%"=="1" (
    echo Installing dependencies. This can take several minutes the first time...
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
    if errorlevel 1 (
        echo.
        echo Failed to install dependencies.
        pause
        exit /b 1
    )
    type nul > "%DEPS_MARKER%"
) else (
    echo Dependencies already installed.
)

echo.
echo Opening app at http://localhost:8000
echo Press Ctrl+C in this window to stop the app.
echo.

".venv\Scripts\python.exe" run_server.py

pause
