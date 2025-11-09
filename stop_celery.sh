#!/bin/bash

# Скрипт остановки Celery workers и beat scheduler

echo "🛑 Stopping Celery workers and beat scheduler..."

if [ -f celery_worker.pid ]; then
    kill $(cat celery_worker.pid) 2>/dev/null && echo "✅ Celery worker stopped" || echo "⚠️  Celery worker was not running"
    rm celery_worker.pid
fi

if [ -f celery_beat.pid ]; then
    kill $(cat celery_beat.pid) 2>/dev/null && echo "✅ Celery beat stopped" || echo "⚠️  Celery beat was not running"
    rm celery_beat.pid
fi

echo "✅ Done!"

