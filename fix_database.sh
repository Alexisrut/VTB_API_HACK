#!/bin/bash

# Script to fix database connection issues

echo "🔧 Fixing database connection issues..."

# Create the database with username name (for default connections)
echo "Creating fastapi_user database (for default connections)..."
docker compose exec -T postgres psql -U fastapi_user -d postgres <<EOF
CREATE DATABASE fastapi_user OWNER fastapi_user;
EOF

# Verify both databases exist
echo ""
echo "📊 Verifying databases..."
docker compose exec postgres psql -U fastapi_user -d fastapi_db -c "\l" | grep -E "fastapi|Name"

echo ""
echo "✅ Database fix completed!"
echo ""
echo "Both databases now exist:"
echo "  - fastapi_db (main application database)"
echo "  - fastapi_user (for default connections)"

