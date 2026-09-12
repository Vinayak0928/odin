@echo off
setlocal

cd /d "%~dp0"
set PORT=8100
set DATA_PATH=.\data\chroma

if not exist "%DATA_PATH%" mkdir "%DATA_PATH%"

where docker >nul 2>&1
if %ERRORLEVEL% equ 0 (
    docker info >nul 2>&1
    if %ERRORLEVEL% equ 0 (
        echo [INFO] Docker detected. Starting ChromaDB container...
        docker compose -f docker-compose.chroma.yml up -d
        echo [SUCCESS] ChromaDB running in Docker at http://localhost:%PORT%
        goto :eof
    )
)

echo [INFO] Docker not detected. Falling back to local ChromaDB service...

set "PY_CMD="
if exist ".\venv\Scripts\python.exe" (
    ".\venv\Scripts\python.exe" -c "import sys" >nul 2>&1
    if not errorlevel 1 set "PY_CMD=.\venv\Scripts\python.exe"
)

if not defined PY_CMD (
    where py >nul 2>&1
    if not errorlevel 1 (
        set "PY_CMD=py"
    ) else (
        where python >nul 2>&1
        if not errorlevel 1 set "PY_CMD=python"
    )
)

if defined PY_CMD (
    echo [SUCCESS] Launching local ChromaDB on http://127.0.0.1:%PORT%...
    %PY_CMD% -m chromadb.cli.cli run --path "%DATA_PATH%" --port %PORT% --host 127.0.0.1
    goto :eof
)

if exist ".\venv\Scripts\chroma.exe" (
    echo [SUCCESS] Launching local ChromaDB on http://127.0.0.1:%PORT%...
    .\venv\Scripts\chroma.exe run --path "%DATA_PATH%" --port %PORT% --host 127.0.0.1
    goto :eof
)

where chroma >nul 2>&1
if not errorlevel 1 (
    chroma run --path "%DATA_PATH%" --port %PORT% --host 127.0.0.1
    goto :eof
)

echo [ERROR] Python environment not found for ChromaDB service.
pause
exit /b 1
