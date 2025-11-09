#!/bin/bash

# Stop all Docker services
# This script stops all containers created by docker.sh

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🛑 Stopping all Docker services...${NC}"
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}❌ Error: Docker is not running.${NC}"
    exit 1
fi

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check which compose file has running services
DEV_RUNNING=false
PROD_RUNNING=false

if docker compose ps 2>/dev/null | grep -q "Up"; then
    DEV_RUNNING=true
fi

if docker compose -f docker-compose.prod.yml ps 2>/dev/null | grep -q "Up"; then
    PROD_RUNNING=true
fi

# Stop development environment if running
if [ "$DEV_RUNNING" = true ]; then
    echo -e "${BLUE}Stopping development environment...${NC}"
    docker compose down
    echo -e "${GREEN}✅ Development environment stopped${NC}"
    echo ""
fi

# Stop production environment if running
if [ "$PROD_RUNNING" = true ]; then
    echo -e "${BLUE}Stopping production environment...${NC}"
    docker compose -f docker-compose.prod.yml down
    echo -e "${GREEN}✅ Production environment stopped${NC}"
    echo ""
fi

# If nothing was running
if [ "$DEV_RUNNING" = false ] && [ "$PROD_RUNNING" = false ]; then
    echo -e "${YELLOW}No running services found.${NC}"
    exit 0
fi

echo -e "${GREEN}✅ All Docker services stopped!${NC}"
echo ""
echo -e "${BLUE}💡 Useful commands:${NC}"
echo "   Start services:     ./docker.sh start"
echo "   Remove volumes:     ./docker.sh clean"
echo "   View status:        ./docker.sh status"
echo ""

