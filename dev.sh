#!/usr/bin/env bash
# Developer workflow utility script for Personal Knowledge Base with Temporal Memory.
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMMAND="${1:-help}"

case "$COMMAND" in
    test)
        echo "Running fast temporal & grounding test suite..."
        pytest personal-kb/tests/test_chunking.py \
               personal-kb/tests/test_temporal_extraction.py \
               personal-kb/tests/test_deduplication.py \
               personal-kb/tests/test_llm_fallback.py \
               personal-kb/tests/test_response_generation.py \
               -v
        ;;
    lint)
        echo "Running Ruff linter..."
        ruff check personal-kb/src
        ;;
    dev)
        echo "Starting Docker stack with LIVE HOT-RELOAD..."
        docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d
        echo "App is live with hot-reload at http://localhost:8000"
        ;;
    up)
        echo "Starting production Docker Compose stack..."
        docker compose up -d --build
        echo "App is live at http://localhost:8000"
        ;;
    down)
        echo "Stopping Docker Compose stack..."
        docker compose down
        ;;
    logs)
        docker compose logs -f app
        ;;
    status)
        docker compose ps
        ;;
    build)
        docker compose build
        ;;
    *)
        echo "Personal Knowledge Base - Commands:"
        echo "  ./dev.sh test     - Run fast temporal unit tests"
        echo "  ./dev.sh lint     - Run code quality check"
        echo "  ./dev.sh dev      - Start Docker container with live hot-reload"
        echo "  ./dev.sh up       - Start production Docker container stack"
        echo "  ./dev.sh down     - Stop all running containers"
        echo "  ./dev.sh logs     - Follow app container logs"
        echo "  ./dev.sh status   - View container health and status"
        echo "  ./dev.sh build    - Rebuild the Docker image"
        ;;
esac
