# Docker Structure

This document describes the restructured Docker setup for the VTB API Hack project.

## Structure

```
.
├── docker.sh                    # Main wrapper script (use this!)
├── docker/
│   ├── docker.sh               # Unified Docker management script
│   └── README.md               # Detailed Docker documentation
├── docker-compose.yml           # Development configuration
├── docker-compose.prod.yml      # Production configuration
├── Dockerfile                   # Backend Dockerfile
└── frontend/
    ├── Dockerfile               # Frontend production Dockerfile
    └── Dockerfile.dev           # Frontend development Dockerfile
```

## Quick Start

### Development

```bash
# Start development environment
./docker.sh start

# View logs
./docker.sh logs

# Stop services
./docker.sh stop
```

### Production

```bash
# Start production environment
./docker.sh start prod

# View logs
./docker.sh logs

# Stop services
./docker.sh stop
```

## Unified Commands

All Docker operations are now handled through a single script:

| Command | Description |
|---------|-------------|
| `./docker.sh start [dev\|prod]` | Start services (default: dev) |
| `./docker.sh stop` | Stop all running services |
| `./docker.sh restart [service]` | Restart all or specific service |
| `./docker.sh logs [service]` | View logs (all or specific service) |
| `./docker.sh rebuild [service]` | Rebuild services |
| `./docker.sh status` | Show service status |
| `./docker.sh clean` | Remove volumes (database data) |
| `./docker.sh help` | Show help message |

## Migration from Old Scripts

The following old scripts have been removed and replaced by `./docker.sh`:

- ❌ `docker-start-dev.sh` → ✅ `./docker.sh start`
- ❌ `docker-start-prod.sh` → ✅ `./docker.sh start prod`
- ❌ `docker-stop.sh` → ✅ `./docker.sh stop`
- ❌ `docker-logs.sh` → ✅ `./docker.sh logs`
- ❌ `docker-rebuild.sh` → ✅ `./docker.sh rebuild`

## Benefits

1. **Single entry point**: One script handles all Docker operations
2. **Better organization**: All Docker scripts in `docker/` directory
3. **Consistent interface**: Same commands for dev and prod
4. **Auto-detection**: Automatically detects which environment is running
5. **Better error handling**: Improved checks and user feedback
6. **Cleaner structure**: Removed redundant scripts

## Examples

```bash
# Start development
./docker.sh start

# Start production
./docker.sh start prod

# View all logs
./docker.sh logs

# View specific service logs
./docker.sh logs app
./docker.sh logs frontend

# Rebuild a service
./docker.sh rebuild frontend

# Restart a service
./docker.sh restart app

# Check status
./docker.sh status

# Clean everything (removes database)
./docker.sh clean
```

For more details, see [docker/README.md](docker/README.md).

