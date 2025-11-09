#!/bin/bash

# Скрипт запуска Multi-Banking MVP

set -e

echo "🚀 Starting Multi-Banking MVP..."

# Проверка наличия .env файла
if [ ! -f .env ]; then
    echo "⚠️  .env file not found. Creating from env.example..."
    if [ -f env.example ]; then
        cp env.example .env
        echo "✅ Created .env file. Please update it with your settings."
    else
        echo "❌ env.example not found. Please create .env manually."
        exit 1
    fi
fi

# Определение команды Docker Compose (поддержка V1 и V2)
# Используем docker compose (V2) по умолчанию, fallback на docker-compose (V1)
set +e
if docker compose version > /dev/null 2>&1; then
    DOCKER_COMPOSE_CMD=("docker" "compose")
elif docker-compose version > /dev/null 2>&1; then
    DOCKER_COMPOSE_CMD=("docker-compose")
else
    echo "❌ Docker Compose not found. Please install Docker Compose."
    exit 1
fi
set -e

# Запуск PostgreSQL и Redis через Docker Compose
echo "📦 Starting PostgreSQL and Redis..."
"${DOCKER_COMPOSE_CMD[@]}" up -d postgres redis

# Ожидание готовности сервисов
echo "⏳ Waiting for services to be ready..."
sleep 5

# Проверка подключения к PostgreSQL
until "${DOCKER_COMPOSE_CMD[@]}" exec -T postgres pg_isready -U fastapi_user > /dev/null 2>&1; do
    echo "   Waiting for PostgreSQL..."
    sleep 2
done

# Проверка подключения к Redis
until "${DOCKER_COMPOSE_CMD[@]}" exec -T redis redis-cli ping > /dev/null 2>&1; do
    echo "   Waiting for Redis..."
    sleep 2
done

echo "✅ Services are ready!"

# Активация виртуального окружения (если существует)
if [ -d "venv" ]; then
    echo "🐍 Activating virtual environment..."
    source venv/bin/activate
fi

# Установка зависимостей (если нужно)
if [ "$1" == "--install" ]; then
    echo "📥 Installing dependencies..."
    pip install -r requirements.txt
fi

# Запуск приложения
echo "🌟 Starting FastAPI application..."
echo "   API will be available at: http://localhost:8000"
echo "   API docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

uvicorn main:app --host 0.0.0.0 --port 8000 --reload

