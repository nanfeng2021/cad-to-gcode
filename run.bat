@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ╔════════════════════════════════════════════════════════╗
echo ║     CAD to G-code Platform - Quick Start              ║
echo ╚════════════════════════════════════════════════════════╝
echo.

REM Check if Python is installed
python --version >nul 2>nul
if %errorlevel% neq 0 (
    echo ✗ Python is not installed!
    echo.
    echo   Please install Python from:
    echo   https://www.python.org/downloads/
    echo.
    echo   Or from Microsoft Store: Search "Python 3.11"
    echo.
    pause
    exit /b 1
)

echo ✓ Python found
python --version
echo.

REM Check if virtual environment exists
if not exist "venv\Scripts\activate.bat" (
    echo 📦 Creating virtual environment...
    python -m venv venv
    echo ✓ Virtual environment created
    echo.
) else (
    echo ✓ Virtual environment found
    echo.
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat
echo.

REM Check if dependencies are installed
python -c "import fastapi" >nul 2>nul
if %errorlevel% neq 0 (
    echo 📥 Installing dependencies...
    echo    This may take a few minutes...
    echo.
    pip install -e . -q
    if %errorlevel% neq 0 (
        echo.
        echo ✗ Installation failed. Trying with Tsinghua mirror...
        pip install -e . -i https://pypi.tuna.tsinghua.edu.cn/simple -q
    )
    echo ✓ Dependencies installed
    echo.
) else (
    echo ✓ Dependencies already installed
    echo.
)

REM Show menu
:MENU
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.
echo Choose an option:
echo.
echo   1. Start API Server (Web interface)
echo   2. Run Quick Test (No installation needed)
echo   3. View Generated G-code Files
echo   4. Open API Documentation in Browser
echo   5. Exit
echo.
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.
set /p choice="Enter your choice (1-5): "

if "%choice%"=="1" goto START_API
if "%choice%"=="2" goto RUN_TEST
if "%choice%"=="3" goto VIEW_FILES
if "%choice%"=="4" goto OPEN_DOCS
if "%choice%"=="5" goto EXIT
if "%choice%"=="" goto MENU

echo Invalid choice. Please try again.
echo.
goto MENU

:START_API
echo.
echo 🚀 Starting API server...
echo.
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.
echo   📖 API Documentation: http://localhost:8000/docs
echo   ❤️ Health Check:      http://localhost:8000/health
echo   📊 Materials List:    http://localhost:8000/materials
echo.
echo   Press Ctrl+C to stop the server
echo.
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.
uvicorn src.web.api:app --reload --host 0.0.0.0 --port 8000
goto MENU

:RUN_TEST
echo.
echo 🧪 Running quick test...
echo.
python scripts\minimal_test.py
echo.
pause
goto MENU

:VIEW_FILES
echo.
echo 📁 Opening output directory...
echo.
explorer "%CD%\output"
goto MENU

:OPEN_DOCS
echo.
echo 🌐 Opening API documentation...
echo.
start http://localhost:8000/docs
echo   If browser didn't open, manually visit:
echo   http://localhost:8000/docs
echo.
pause
goto MENU

:EXIT
echo.
echo 👋 Goodbye!
echo.
exit /b 0
