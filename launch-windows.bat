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

if exist ".\venv\Scripts\python.exe" (
    .\venv\Scripts\python.exe -m uvicorn app:app --host 127.0.0.1 --port 7000
) else (
    python -m uvicorn app:app --host 127.0.0.1 --port 7000
)
