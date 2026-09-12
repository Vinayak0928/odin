<#
.SYNOPSIS
    Starts ChromaDB on localhost:8100 for the Odysseus RAG pipeline.
.DESCRIPTION
    Checks if Docker is available and running. If Docker is ready, it starts
    ChromaDB using docker-compose.chroma.yml. If Docker is not available,
    it starts ChromaDB locally using the installed Python virtual environment.
#>

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $ScriptDir

$Port = 8100
$DataPath = Join-Path $ScriptDir "data\chroma"

if (-not (Test-Path $DataPath)) {
    New-Item -ItemType Directory -Path $DataPath -Force | Out-Null
}

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  Starting ChromaDB for Odysseus RAG (Port: $Port)       " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# Check if docker is installed and running
$hasDocker = $false
try {
    $dockerCmd = Get-Command docker -ErrorAction SilentlyContinue
    if ($dockerCmd) {
        docker info 2>&1 | Out-Null
        if ($LASTEXITCODE -eq 0) {
            $hasDocker = $true
        }
    }
} catch {
    $hasDocker = $false
}

if ($hasDocker) {
    Write-Host "[INFO] Docker detected and active. Starting ChromaDB container..." -ForegroundColor Green
    docker compose -f docker-compose.chroma.yml up -d
    Write-Host "[SUCCESS] ChromaDB is running in Docker at http://localhost:$Port" -ForegroundColor Green
    Write-Host "To view logs: docker compose -f docker-compose.chroma.yml logs -f" -ForegroundColor Gray
    Write-Host "To stop:      docker compose -f docker-compose.chroma.yml down" -ForegroundColor Gray
    exit 0
}

Write-Host "[INFO] Docker is not available or not running on this host." -ForegroundColor Yellow
Write-Host "[INFO] Falling back to local native ChromaDB service..." -ForegroundColor Yellow

$chromaExe = Join-Path $ScriptDir "venv\Scripts\chroma.exe"
if (-not (Test-Path $chromaExe)) {
    $chromaExe = (Get-Command chroma.exe -ErrorAction SilentlyContinue).Source
}

if (-not $chromaExe -or -not (Test-Path $chromaExe)) {
    Write-Host "[ERROR] Chroma CLI not found. Please install Docker Desktop or run: .\venv\Scripts\pip install chromadb" -ForegroundColor Red
    exit 1
}

Write-Host "[SUCCESS] Launching local ChromaDB server on http://localhost:$Port..." -ForegroundColor Green
Write-Host "Press Ctrl+C to stop the ChromaDB server." -ForegroundColor Gray
& $chromaExe run --path "$DataPath" --port $Port
