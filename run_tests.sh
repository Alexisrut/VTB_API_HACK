#!/bin/bash

# Script to run backend tests

echo "🧪 Running backend tests..."

# Check if we're in a virtual environment
if [ -z "$VIRTUAL_ENV" ]; then
    echo "⚠️  Warning: Not in a virtual environment"
    echo "   Consider activating your venv first: source venv/bin/activate"
fi

# Install test dependencies if needed
echo "📦 Checking dependencies..."
pip install -q pytest pytest-asyncio pytest-cov aiosqlite httpx

# Run tests
echo "🚀 Running tests..."
pytest tests/ -v --tb=short

# Optionally run with coverage
if [ "$1" == "--coverage" ] || [ "$1" == "-c" ]; then
    echo "📊 Running with coverage..."
    pytest tests/ --cov=app --cov-report=html --cov-report=term
    echo "📄 Coverage report generated in htmlcov/index.html"
fi

echo "✅ Tests completed!"

