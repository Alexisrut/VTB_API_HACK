#!/bin/bash

# Скрипт остановки Multi-Banking MVP

set -e

echo "🛑 Stopping Multi-Banking MVP services..."

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

# Остановка контейнеров
echo "📦 Stopping containers..."
"${DOCKER_COMPOSE_CMD[@]}" stop postgres redis

echo "✅ Containers stopped successfully!"
echo ""
echo "To start again, run: ./start.sh"
echo "To remove containers completely, run: docker compose down"

