<#
.SYNOPSIS
    Starts the EpiSwarm development environment (FastAPI Backend + Vite Frontend).
.DESCRIPTION
    Runs the FastAPI backend with hot reloading on port 8000 and optionally launches the Vite dev server on port 3000.
#>

param (
    [switch]$BackendOnly,
    [switch]$FrontendOnly
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir

Set-Location $ProjectRoot
$env:PYTHONPATH = "$ProjectRoot\src"

if ($FrontendOnly) {
    Write-Host "Starting Vite dev server on http://localhost:3000 ..." -ForegroundColor Cyan
    Set-Location "$ProjectRoot\web"
    npm run dev
    return
}

if ($BackendOnly) {
    Write-Host "Starting FastAPI backend on http://localhost:8000 ..." -ForegroundColor Cyan
    uvicorn episwarm.api.main:app --reload --host 127.0.0.1 --port 8000
    return
}

Write-Host "==========================================================" -ForegroundColor Green
Write-Host "         EpiSwarm Full-Stack Development Runner          " -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Green
Write-Host "FastAPI Backend:  http://127.0.0.1:8000" -ForegroundColor Yellow
Write-Host "Interactive Docs: http://127.0.0.1:8000/docs" -ForegroundColor Yellow
Write-Host "Vite Dev Server:  http://127.0.0.1:3000" -ForegroundColor Yellow
Write-Host "----------------------------------------------------------" -ForegroundColor Gray

Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$ProjectRoot\web'; npm run dev"
uvicorn episwarm.api.main:app --reload --host 127.0.0.1 --port 8000
