<#
.SYNOPSIS
  Developer workflow utility script for Personal Knowledge Base with Temporal Memory.
.DESCRIPTION
  Simplifies common development, testing, and Docker operations.
.EXAMPLE
  .\dev.ps1 test       # Runs the fast unit & temporal tests
  .\dev.ps1 lint       # Runs Ruff linter
  .\dev.ps1 dev        # Launches Docker with live hot-reloading
  .\dev.ps1 up         # Launches production Docker Compose stack
  .\dev.ps1 down       # Stops Docker Compose stack
  .\dev.ps1 logs       # Views real-time application logs
  .\dev.ps1 status     # Checks status of Docker services
#>

param(
    [Parameter(Position=0)]
    [ValidateSet("test", "lint", "dev", "up", "down", "logs", "status", "build", "help")]
    [string]$Command = "help"
)

$ErrorActionPreference = "Stop"
$RootDir = $PSScriptRoot
$PersonalKbDir = Join-Path $RootDir "personal-kb"

switch ($Command) {
    "test" {
        Write-Host "Running fast temporal & grounding test suite..." -ForegroundColor Cyan
        & "$RootDir\.venv\Scripts\pytest.exe" "$PersonalKbDir\tests\test_chunking.py" `
                                             "$PersonalKbDir\tests\test_temporal_extraction.py" `
                                             "$PersonalKbDir\tests\test_deduplication.py" `
                                             "$PersonalKbDir\tests\test_llm_fallback.py" `
                                             "$PersonalKbDir\tests\test_response_generation.py" -v
    }

    "lint" {
        Write-Host "Running Ruff linter..." -ForegroundColor Cyan
        & "$RootDir\.venv\Scripts\ruff.exe" check "$PersonalKbDir\src"
    }

    "dev" {
        Write-Host "Starting Docker stack with LIVE HOT-RELOAD..." -ForegroundColor Green
        docker compose -f "$RootDir\docker-compose.yml" -f "$RootDir\docker-compose.dev.yml" up -d
        Write-Host "App is live with hot-reload at http://localhost:8000 (UI: http://localhost:8000/ui)" -ForegroundColor Yellow
    }

    "up" {
        Write-Host "Starting production Docker Compose stack..." -ForegroundColor Green
        docker compose -f "$RootDir\docker-compose.yml" up -d --build
        Write-Host "App is live at http://localhost:8000 (UI: http://localhost:8000/ui)" -ForegroundColor Yellow
    }

    "down" {
        Write-Host "Stopping Docker Compose stack..." -ForegroundColor Yellow
        docker compose -f "$RootDir\docker-compose.yml" down
    }

    "logs" {
        docker compose -f "$RootDir\docker-compose.yml" logs -f app
    }

    "status" {
        docker compose -f "$RootDir\docker-compose.yml" ps
    }

    "build" {
        Write-Host "Building Docker image..." -ForegroundColor Cyan
        docker compose -f "$RootDir\docker-compose.yml" build
    }

    default {
        Write-Host "Personal Knowledge Base - Development Commands:" -ForegroundColor Cyan
        Write-Host "  .\dev.ps1 test     - Run fast temporal unit tests (same as CI)"
        Write-Host "  .\dev.ps1 lint     - Run code quality and linter checks"
        Write-Host "  .\dev.ps1 dev      - Start Docker container with LIVE hot-reload for src/"
        Write-Host "  .\dev.ps1 up       - Start production Docker container stack"
        Write-Host "  .\dev.ps1 down     - Stop all running containers"
        Write-Host "  .\dev.ps1 logs     - Follow app container logs"
        Write-Host "  .\dev.ps1 status   - View container health and status"
        Write-Host "  .\dev.ps1 build    - Rebuild the Docker image"
    }
}
