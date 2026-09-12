@echo off
setlocal
cd /d "%~dp0"

echo ==========================================================================
echo  [SIH26117] Starting MRPL Sovereign AI Workbench on http://127.0.0.1:7000
echo ==========================================================================

echo [INFO] Checking ChromaDB service on port 8100...
netstat -ano | findstr :8100 | findstr LISTENING >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [INFO] Starting ChromaDB background service...
    start /b "" cmd /c "%~dp0run-chromadb.bat"
    timeout /t 3 /nobreak >nul
)

:: Locate a working Python interpreter
set "PY_CMD="

:: 1. Check if existing venv is functional on this machine
if exist ".\venv\Scripts\python.exe" (
    ".\venv\Scripts\python.exe" -c "import sys" >nul 2>&1
    if not errorlevel 1 (
        set "PY_CMD=.\venv\Scripts\python.exe"
    ) else (
        echo [WARN] Virtual environment contains invalid paths from another machine.
    )
)

:: 2. Find system Python if venv is missing or invalid
if not defined PY_CMD (
    set "SYS_PY="
    where py >nul 2>&1
    if not errorlevel 1 (
        py -3.12 -c "import sys" >nul 2>&1
        if not errorlevel 1 (
            set "SYS_PY=py -3.12"
        ) else (
            py -3.11 -c "import sys" >nul 2>&1
            if not errorlevel 1 (
                set "SYS_PY=py -3.11"
            ) else (
                set "SYS_PY=py"
            )
        )
    )
    if not defined SYS_PY (
        where python >nul 2>&1
        if not errorlevel 1 (
            set "SYS_PY=python"
        )
    )

    if defined SYS_PY (
        if exist ".\venv\Scripts\python.exe" (
            echo [INFO] Re-creating virtual environment for this PC...
            rmdir /s /q ".\venv" >nul 2>&1
            %SYS_PY% -m venv venv >nul 2>&1
            if exist ".\venv\Scripts\python.exe" (
                echo [INFO] Installing requirements in virtual environment...
                ".\venv\Scripts\python.exe" -m pip install -r requirements.txt >nul 2>&1
                set "PY_CMD=.\venv\Scripts\python.exe"
            )
        )
        if not defined PY_CMD (
            set "PY_CMD=%SYS_PY%"
        )
    )
)

if not defined PY_CMD (
    echo [ERROR] Python 3.11+ was not found on this system.
    echo Please install Python 3.11+ from https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [INFO] Using Python: %PY_CMD%
%PY_CMD% -m uvicorn app:app --host 127.0.0.1 --port 7000
