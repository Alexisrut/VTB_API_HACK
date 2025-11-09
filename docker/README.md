# Docker Management

This directory contains unified Docker management scripts for the VTB API Hack project.

## Quick Start

From the project root, use the unified Docker script:

```bash
./docker.sh [command] [options]
```

Or directly:

```bash
./docker/docker.sh [command] [options]
```

## Available Commands

### Start Services

```bash
# Start development environment (default)
./docker.sh start
# or
./docker.sh start dev

# Start production environment
./docker.sh start prod
```

### Stop Services

```bash
./docker.sh stop
```

### View Logs

```bash
# View all logs
./docker.sh logs

# View specific service logs
./docker.sh logs app
./docker.sh logs frontend
./docker.sh logs postgres
./docker.sh logs redis
```

### Rebuild Services

```bash
# Rebuild all services (dev)
./docker.sh rebuild

# Rebuild specific service
./docker.sh rebuild frontend
./docker.sh rebuild app

# Rebuild for production
./docker.sh rebuild frontend prod
```

### Restart Services

```bash
# Restart all services
./docker.sh restart

# Restart specific service
./docker.sh restart app
```

### Check Status

```bash
./docker.sh status
```

### Clean Volumes

```bash
# Remove all volumes (including database data)
./docker.sh clean
```

## Service Access Points

### Development Environment

- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **PostgreSQL**: localhost:5434
- **Redis**: localhost:6381

### Production Environment

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

## Troubleshooting

### Services won't start

1. Check Docker is running: `docker info`
2. Check logs: `./docker.sh logs`
3. Rebuild services: `./docker.sh rebuild`

### Database issues

1. Check postgres logs: `./docker.sh logs postgres`
2. Clean and restart: `./docker.sh clean && ./docker.sh start`

### Port conflicts

If ports are already in use, check what's using them:

```bash
# macOS/Linux
lsof -i :8000
lsof -i :5173
lsof -i :5434
```

### Reset everything

```bash
./docker.sh stop
./docker.sh clean
./docker.sh start
```

## File Structure

```
docker/
├── docker.sh          # Unified Docker management script
└── README.md          # This file

# Docker compose files (in project root)
├── docker-compose.yml      # Development configuration
└── docker-compose.prod.yml # Production configuration

# Dockerfiles
├── Dockerfile              # Backend Dockerfile
└── frontend/
    ├── Dockerfile          # Frontend production Dockerfile
    └── Dockerfile.dev      # Frontend development Dockerfile
```

