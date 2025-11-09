#!/bin/bash

# Unified Docker Management Script
# Usage: ./docker.sh [command] [options]
# Commands: start, stop, restart, logs, rebuild, status, clean

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Change to project root
cd "$PROJECT_ROOT"

# Docker compose files
COMPOSE_DEV="docker-compose.yml"
COMPOSE_PROD="docker-compose.prod.yml"

# Function to check if Docker is running
check_docker() {
    if ! docker info > /dev/null 2>&1; then
        echo -e "${RED}❌ Error: Docker is not running. Please start Docker and try again.${NC}"
        exit 1
    fi
}

# Function to check if .env exists
check_env() {
    if [ ! -f .env ]; then
        if [ "$1" = "prod" ]; then
            echo -e "${RED}❌ Error: .env file not found. Please create it from env.example${NC}"
            exit 1
        else
            echo -e "${YELLOW}⚠️  Warning: .env file not found. Creating from env.example...${NC}"
            cp env.example .env
            echo -e "${GREEN}✅ Created .env file. Please update it with your configuration.${NC}"
        fi
    fi
}

# Function to detect which compose file is active
detect_compose_file() {
    if docker compose ps 2>/dev/null | grep -q "Up"; then
        echo "$COMPOSE_DEV"
    elif docker compose -f "$COMPOSE_PROD" ps 2>/dev/null | grep -q "Up"; then
        echo "$COMPOSE_PROD"
    else
        echo ""
    fi
}

# Function to get compose command
get_compose_cmd() {
    local env=${1:-dev}
    if [ "$env" = "prod" ]; then
        echo "docker compose -f $COMPOSE_PROD"
    else
        echo "docker compose"
    fi
}

# Start services
start_services() {
    local env=${1:-dev}
    local compose_cmd=$(get_compose_cmd "$env")
    
    check_docker
    check_env "$env"
    
    echo -e "${BLUE}🚀 Starting ${env} environment...${NC}"
    echo ""
    
    echo -e "${BLUE}🔨 Building and starting containers...${NC}"
    $compose_cmd up -d --build
    
    # Wait for services
    echo ""
    echo -e "${BLUE}⏳ Waiting for services to be ready...${NC}"
    sleep $([ "$env" = "prod" ] && echo "10" || echo "5")
    
    # Show status
    echo ""
    echo -e "${BLUE}📊 Service Status:${NC}"
    $compose_cmd ps
    
    echo ""
    echo -e "${GREEN}✅ ${env} environment started!${NC}"
    echo ""
    
    if [ "$env" = "dev" ]; then
        echo -e "${BLUE}📍 Access points:${NC}"
        echo "   Frontend:  http://localhost:5173"
        echo "   Backend:   http://localhost:8000"
        echo "   API Docs:  http://localhost:8000/docs"
        echo "   PostgreSQL: localhost:5434"
        echo "   Redis:     localhost:6381"
    else
        echo -e "${BLUE}📍 Access points:${NC}"
        echo "   Frontend:  http://localhost:3000"
        echo "   Backend:   http://localhost:8000"
        echo "   API Docs:  http://localhost:8000/docs"
    fi
    
    echo ""
    echo -e "${BLUE}📝 Useful commands:${NC}"
    echo "   View logs:     ./docker.sh logs [service]"
    echo "   Stop services: ./docker.sh stop"
    echo "   Status:        ./docker.sh status"
    echo ""
}

# Stop services
stop_services() {
    check_docker
    
    local active_file=$(detect_compose_file)
    
    if [ -z "$active_file" ]; then
        echo -e "${YELLOW}No running services found.${NC}"
        exit 0
    fi
    
    local compose_cmd
    if [ "$active_file" = "$COMPOSE_PROD" ]; then
        compose_cmd=$(get_compose_cmd "prod")
        echo -e "${BLUE}🛑 Stopping production environment...${NC}"
    else
        compose_cmd=$(get_compose_cmd "dev")
        echo -e "${BLUE}🛑 Stopping development environment...${NC}"
    fi
    
    $compose_cmd down
    
    echo ""
    echo -e "${GREEN}✅ All services stopped!${NC}"
    echo ""
    echo -e "${BLUE}💡 To remove volumes (database data), use:${NC}"
    echo "   ./docker.sh clean"
    echo ""
}

# Restart services
restart_services() {
    local service=$1
    check_docker
    
    local active_file=$(detect_compose_file)
    
    if [ -z "$active_file" ]; then
        echo -e "${YELLOW}No running services found. Starting development environment...${NC}"
        start_services "dev"
        return
    fi
    
    local compose_cmd
    if [ "$active_file" = "$COMPOSE_PROD" ]; then
        compose_cmd=$(get_compose_cmd "prod")
    else
        compose_cmd=$(get_compose_cmd "dev")
    fi
    
    if [ -z "$service" ]; then
        echo -e "${BLUE}🔄 Restarting all services...${NC}"
        $compose_cmd restart
    else
        echo -e "${BLUE}🔄 Restarting service: $service${NC}"
        $compose_cmd restart "$service"
    fi
    
    echo ""
    echo -e "${GREEN}✅ Restart complete!${NC}"
    echo ""
    $compose_cmd ps
}

# View logs
view_logs() {
    local service=$1
    check_docker
    
    local active_file=$(detect_compose_file)
    
    if [ -z "$active_file" ]; then
        echo -e "${YELLOW}No running services found.${NC}"
        exit 1
    fi
    
    local compose_cmd
    if [ "$active_file" = "$COMPOSE_PROD" ]; then
        compose_cmd=$(get_compose_cmd "prod")
    else
        compose_cmd=$(get_compose_cmd "dev")
    fi
    
    if [ -z "$service" ]; then
        echo -e "${BLUE}📋 Showing logs for all services...${NC}"
        echo -e "${BLUE}   Use: ./docker.sh logs [service_name] to view specific service${NC}"
        echo -e "${BLUE}   Available services: frontend, app, postgres, redis${NC}"
        echo ""
        $compose_cmd logs -f
    else
        echo -e "${BLUE}📋 Showing logs for: $service${NC}"
        echo ""
        $compose_cmd logs -f "$service"
    fi
}

# Rebuild services
rebuild_services() {
    local service=$1
    local env=${2:-dev}
    check_docker
    
    local compose_cmd=$(get_compose_cmd "$env")
    
    if [ -z "$service" ]; then
        echo -e "${BLUE}🔨 Rebuilding all services...${NC}"
        $compose_cmd up -d --build
    else
        echo -e "${BLUE}🔨 Rebuilding service: $service${NC}"
        $compose_cmd up -d --build "$service"
    fi
    
    echo ""
    echo -e "${GREEN}✅ Rebuild complete!${NC}"
    echo ""
    $compose_cmd ps
}

# Show status
show_status() {
    check_docker
    
    echo -e "${BLUE}📊 Service Status:${NC}"
    echo ""
    
    # Check dev
    if docker compose ps 2>/dev/null | grep -q "Up"; then
        echo -e "${GREEN}Development Environment:${NC}"
        docker compose ps
        echo ""
    fi
    
    # Check prod
    if docker compose -f "$COMPOSE_PROD" ps 2>/dev/null | grep -q "Up"; then
        echo -e "${GREEN}Production Environment:${NC}"
        docker compose -f "$COMPOSE_PROD" ps
        echo ""
    fi
    
    if ! docker compose ps 2>/dev/null | grep -q "Up" && ! docker compose -f "$COMPOSE_PROD" ps 2>/dev/null | grep -q "Up"; then
        echo -e "${YELLOW}No services are currently running.${NC}"
        echo ""
        echo "Start services with:"
        echo "   ./docker.sh start        # Development"
        echo "   ./docker.sh start prod   # Production"
    fi
}

# Clean (remove volumes)
clean_volumes() {
    check_docker
    
    local active_file=$(detect_compose_file)
    
    if [ -z "$active_file" ]; then
        echo -e "${YELLOW}No running services found. Cleaning all volumes...${NC}"
        docker compose down -v 2>/dev/null || true
        docker compose -f "$COMPOSE_PROD" down -v 2>/dev/null || true
    else
        local compose_cmd
        if [ "$active_file" = "$COMPOSE_PROD" ]; then
            compose_cmd=$(get_compose_cmd "prod")
        else
            compose_cmd=$(get_compose_cmd "dev")
        fi
        
        echo -e "${YELLOW}⚠️  Warning: This will remove all volumes including database data!${NC}"
        read -p "Are you sure? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            $compose_cmd down -v
            echo -e "${GREEN}✅ Volumes removed!${NC}"
        else
            echo -e "${BLUE}Cancelled.${NC}"
        fi
    fi
}

# Show help
show_help() {
    echo -e "${BLUE}Docker Management Script${NC}"
    echo ""
    echo "Usage: ./docker.sh [command] [options]"
    echo ""
    echo "Commands:"
    echo "  start [dev|prod]     Start services (default: dev)"
    echo "  stop                 Stop all running services"
    echo "  restart [service]    Restart all services or specific service"
    echo "  logs [service]       View logs (all services or specific service)"
    echo "  rebuild [service]    Rebuild services (default: dev)"
    echo "  status               Show status of all services"
    echo "  clean                Remove volumes (database data)"
    echo "  help                 Show this help message"
    echo ""
    echo "Examples:"
    echo "  ./docker.sh start              # Start development environment"
    echo "  ./docker.sh start prod         # Start production environment"
    echo "  ./docker.sh logs               # View all logs"
    echo "  ./docker.sh logs app           # View app logs"
    echo "  ./docker.sh rebuild frontend    # Rebuild frontend service"
    echo "  ./docker.sh restart            # Restart all services"
    echo "  ./docker.sh restart app        # Restart app service"
    echo "  ./docker.sh status             # Show service status"
    echo "  ./docker.sh stop               # Stop all services"
    echo "  ./docker.sh clean              # Remove volumes"
    echo ""
}

# Main command handler
case "${1:-help}" in
    start)
        start_services "${2:-dev}"
        ;;
    stop)
        stop_services
        ;;
    restart)
        restart_services "$2"
        ;;
    logs)
        view_logs "$2"
        ;;
    rebuild)
        rebuild_services "$2" "${3:-dev}"
        ;;
    status)
        show_status
        ;;
    clean)
        clean_volumes
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        echo -e "${RED}Unknown command: $1${NC}"
        echo ""
        show_help
        exit 1
        ;;
esac

