#!/bin/bash

# Скрипт запуска Celery workers и beat scheduler

set -e

echo "🔄 Starting Celery workers and beat scheduler..."

# Активация виртуального окружения (если существует)
if [ -d "venv" ]; then
    echo "🐍 Activating virtual environment..."
    source venv/bin/activate
fi

# Определение команды Docker Compose (поддержка V1 и V2)
if command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE="docker-compose"
elif docker compose version &> /dev/null; then
    DOCKER_COMPOSE="docker compose"
else
    DOCKER_COMPOSE="docker compose"
fi

# Проверка наличия Redis
if ! $DOCKER_COMPOSE ps redis 2>/dev/null | grep -q "Up"; then
    echo "⚠️  Redis is not running. Starting Redis..."
    $DOCKER_COMPOSE up -d redis
    sleep 3
fi

# Запуск Celery worker в фоне
echo "👷 Starting Celery worker..."
celery -A app.tasks.sync_tasks.celery_app worker --loglevel=info --detach --pidfile=celery_worker.pid

# Запуск Celery beat в фоне
echo "⏰ Starting Celery beat scheduler..."
celery -A app.tasks.sync_tasks.celery_app beat --loglevel=info --detach --pidfile=celery_beat.pid

echo "✅ Celery workers and beat scheduler started!"
echo "   Worker PID: $(cat celery_worker.pid)"
echo "   Beat PID: $(cat celery_beat.pid)"
echo ""
echo "To stop workers, run: ./stop_celery.sh"

