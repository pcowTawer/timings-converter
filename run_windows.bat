@echo off
setlocal

set VENV_DIR=%~dp0.venv

if not exist "%VENV_DIR%\Scripts\python.exe" (
    echo Creating virtual environment in %VENV_DIR% ...
    python -m venv "%VENV_DIR%"
    if errorlevel 1 (
        echo Failed to create venv. Make sure Python 3 is installed and on PATH.
        pause
        exit /b 1
    )
)

echo Installing dependencies...
"%VENV_DIR%\Scripts\python.exe" -m pip install --upgrade pip >nul
"%VENV_DIR%\Scripts\python.exe" -m pip install beautifulsoup4

echo Starting Timings Converter...
"%VENV_DIR%\Scripts\pythonw.exe" "%~dp0timings_gui.py"

endlocal
