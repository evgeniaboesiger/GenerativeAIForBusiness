@echo off
echo ==========================================
echo   MATCHA - Setup Script
echo ==========================================
echo.

echo [Step 1/4] Checking Python installation...
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo ERROR: Python not found.
    echo Please install Python first from https://python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)
echo OK - Python found
echo.

echo [Step 2/4] Installing required packages...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo ERROR: Failed to install packages.
    echo Please check your internet connection and try again.
    pause
    exit /b 1
)
echo OK - Packages installed
echo.

echo [Step 3/4] Checking if Ollama is running...
powershell -Command "try { $response = Invoke-WebRequest -Uri 'http://localhost:11434/api/tags' -TimeoutSec 3; Write-Host 'OK - Ollama is running' } catch { Write-Host 'NOTE: Ollama is not running. Demo will use sample data only.' }"
echo.

echo [Step 4/4] Starting MATCHA...
echo.
echo MATCHA will now start. Your browser will open automatically.
echo Keep this window open while using the app.
echo Press Ctrl+C to stop the app when done.
echo.
python -m streamlit run app.py

pause
