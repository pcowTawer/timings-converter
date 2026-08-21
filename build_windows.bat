@echo off
setlocal

set ROOT=%~dp0
set ARTIFACTS=%ROOT%_artifacts
set VENV_DIR=%ARTIFACTS%\venv-windows
set WORK_DIR=%ARTIFACTS%\work-windows
set SPEC_DIR=%ARTIFACTS%\spec-windows
set DIST_DIR=%ARTIFACTS%\dist-windows
set BUILDS_DIR=%ARTIFACTS%\builds
set APP_NAME=Timings.Converter.Windows
set SCRIPT=%ROOT%timings_gui.py

if not exist "%SCRIPT%" (
    echo Не найден файл %SCRIPT%
    echo Если GUI-скрипт называется иначе, поправьте переменную SCRIPT в этом батнике.
    pause
    exit /b 1
)

if not exist "%VENV_DIR%\Scripts\python.exe" (
    echo Creating virtual environment in %VENV_DIR% ...
    python -m venv "%VENV_DIR%"
    if errorlevel 1 (
        echo Failed to create venv. Make sure Python 3 is installed and on PATH.
        pause
        exit /b 1
    )
)

echo Installing/updating dependencies...
"%VENV_DIR%\Scripts\python.exe" -m pip install --upgrade pip >nul
"%VENV_DIR%\Scripts\python.exe" -m pip install --upgrade pyinstaller beautifulsoup4

echo Building %APP_NAME% ...
"%VENV_DIR%\Scripts\pyinstaller.exe" --onefile --windowed --noconfirm ^
    --name "%APP_NAME%" ^
    --workpath "%WORK_DIR%" ^
    --specpath "%SPEC_DIR%" ^
    --distpath "%DIST_DIR%" ^
    "%SCRIPT%"
if errorlevel 1 (
    echo Build failed.
    pause
    exit /b 1
)

if not exist "%BUILDS_DIR%" mkdir "%BUILDS_DIR%"
copy /Y "%DIST_DIR%\%APP_NAME%.exe" "%BUILDS_DIR%\%APP_NAME%.exe" >nul

echo.
echo Готово: %BUILDS_DIR%\%APP_NAME%.exe

endlocal
