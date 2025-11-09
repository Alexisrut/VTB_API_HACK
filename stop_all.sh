#!/bin/bash

# Скрипт полной остановки и удаления контейнеров Multi-Banking MVP

set -e

echo "🛑 Stopping and removing Multi-Banking MVP services..."

# Определение команды Docker Compose (поддержка V1 и V2)
set +e
if docker compose version > /dev/null 2>&1; then
    DOCKER_COMPOSE_CMD=("docker" "compose")
elif docker-compose version > /dev/null 2>&1; then
    DOCKER_COMPOSE_CMD=("docker-compose")
else
    echo "❌ Docker Compose not found."
    exit 1
fi
set -e

# Остановка и удаление контейнеров
echo "📦 Stopping and removing containers..."
"${DOCKER_COMPOSE_CMD[@]}" down

echo "✅ All containers stopped and removed!"
echo ""
echo "⚠️  Note: Data volumes are preserved."
echo "To remove volumes as well, run: docker compose down -v"
echo ""
echo "To start again, run: ./start.sh"

