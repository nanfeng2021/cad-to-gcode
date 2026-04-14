@echo off
REM CAD to G-code Platform - Windows Quick Start Script
REM Usage: start.bat [dev^|prod^|test^|help]

setlocal enabledelayedexpansion

set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%.."
cd /d "%PROJECT_ROOT%"

set "RED=[31m"
set "GREEN=[32m"
set "YELLOW=[33m"
set "BLUE=[34m"
set "NC=[0m"

echo ╔════════════════════════════════════════════════════════╗
echo ║     CAD to G-code Platform - Quick Start              ║
echo ╚════════════════════════════════════════════════════════╝
echo.

REM Check Docker
where docker >nul 2>nul
if %errorlevel% neq 0 (
    echo ✗ Docker is not installed. Please install Docker Desktop first.
    echo   Download from: https://www.docker.com/products/docker-desktop
    exit /b 1
)

docker info >nul 2>nul
if %errorlevel% neq 0 (
    echo ✗ Docker daemon is not running. Please start Docker Desktop.
    exit /b 1
)

echo ✓ Docker is available

REM Check Docker Compose
where docker-compose >nul 2>nul
if %errorlevel% equ 0 (
    set "COMPOSE_CMD=docker-compose"
) else (
    docker compose version >nul 2>nul
    if %errorlevel% equ 0 (
        set "COMPOSE_CMD=docker compose"
    ) else (
        echo ✗ Docker Compose is not installed.
        exit /b 1
    )
)

echo ✓ Docker Compose is available

REM Create directories
if not exist "logs" mkdir logs
if not exist "output" mkdir output
if not exist "data\samples" mkdir data\samples
echo ✓ Directories ready

REM Command handler
if "%~1"=="" goto dev
if /i "%~1"=="dev" goto dev
if /i "%~1"=="development" goto dev
if /i "%~1"=="prod" goto prod
if /i "%~1"=="production" goto prod
if /i "%~1"=="test" goto test
if /i "%~1"=="stop" goto stop
if /i "%~1"=="logs" goto logs
if /i "%~1"=="clean" goto clean
if /i "%~1"=="help" goto help

echo Unknown command: %~1
echo.
goto help

:dev
echo Starting in DEVELOPMENT mode...
echo.
%COMPOSE_CMD% up --build -d
echo.
echo ✓ Services started!
echo.
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.
echo   API Documentation: http://localhost:8000/docs
echo   Health Check:      http://localhost:8000/health
echo   Materials List:    http://localhost:8000/materials
echo.
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.
echo View logs: docker-compose logs -f app
echo Stop:      docker-compose down
echo Shell:     docker-compose exec app bash
echo.
goto :EOF

:prod
echo Starting in PRODUCTION mode...
echo.
docker build -t cad-to-gcode:latest .
docker run -d ^
    -p 8000:8000 ^
    -v %CD%\output:C:\app\output ^
    -v %CD%\logs:C:\app\logs ^
    --name cad2gcode-prod ^
    --restart unless-stopped ^
    cad-to-gcode:latest ^
    uvicorn src.web.api:app --host 0.0.0.0 --port 8000 --workers 2
echo.
echo ✓ Production server started!
echo.
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.
echo   API: http://localhost:8000
echo.
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.
echo View logs: docker logs -f cad2gcode-prod
echo Stop:      docker stop cad2gcode-prod
echo.
goto :EOF

:test
echo Running tests...
echo.
%COMPOSE_CMD% run --rm cli python -m pytest tests/ -v --tb=short
echo.
echo ✓ Tests completed!
goto :EOF

:stop
%COMPOSE_CMD% down
echo ✓ Services stopped
goto :EOF

:logs
%COMPOSE_CMD% logs -f app
goto :EOF

:clean
%COMPOSE_CMD% down -v
docker rm -f cad2gcode-prod 2>nul
echo ✓ Cleanup complete
goto :EOF

:help
echo Usage: start.bat [COMMAND]
echo.
echo Commands:
echo   dev       Start development server with Docker Compose (default)
echo   prod      Start production server with Docker
echo   test      Run test suite
echo   stop      Stop all running containers
echo   logs      View logs
echo   clean     Clean up containers and volumes
echo   help      Show this help message
echo.
echo Examples:
echo   start.bat dev        Start development mode
echo   start.bat prod       Start production mode
echo   start.bat test       Run tests
echo.
goto :EOF
