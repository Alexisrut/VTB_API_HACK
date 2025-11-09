# Docker Desktop I/O Error Fix Guide

## Problem

You're seeing this error:
```
Error response from daemon: error creating temporary lease: 
write /var/lib/desktop-containerd/daemon/io.containerd.metadata.v1.bolt/meta.db: 
input/output error
```

This is a Docker Desktop internal database corruption issue.

## Quick Fix (Recommended)

### Option 1: Restart Docker Desktop

1. **Quit Docker Desktop completely:**
   - Click the Docker icon in your menu bar (top right)
   - Select "Quit Docker Desktop"
   - Wait for it to fully quit

2. **Restart Docker Desktop:**
   - Open Docker Desktop application
   - Wait for it to fully start (whale icon stops animating)
   - This usually takes 30-60 seconds

3. **Verify it's working:**
   ```bash
   docker info
   ```

4. **Try starting the project again:**
   ```bash
   ./docker.sh start
   ```

### Option 2: Use the Fix Script

```bash
# Run the fix script
./fix_docker.sh

# After restarting Docker Desktop, verify:
./fix_docker.sh --verify
```

## Nuclear Option (If restart doesn't work)

**⚠️ WARNING: This will delete ALL Docker containers, images, and volumes!**

1. **Quit Docker Desktop completely**

2. **Remove Docker Desktop data:**
   ```bash
   rm -rf ~/Library/Containers/com.docker.docker/Data
   ```

3. **Restart Docker Desktop**

4. **Verify:**
   ```bash
   docker info
   ```

## Alternative: Run Without Docker

If Docker continues to have issues, you can run the project locally without Docker:

### Prerequisites
- PostgreSQL running locally (or use Docker just for DB)
- Redis running locally (or use Docker just for Redis)

### Steps

1. **Start only database services:**
   ```bash
   docker compose up -d postgres redis
   ```

2. **Set up Python environment:**
   ```bash
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Start the backend:**
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000 --reload
   ```

4. **Start the frontend (in another terminal):**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

## Prevention

To avoid this issue in the future:

1. **Keep Docker Desktop updated**
2. **Don't force-quit Docker Desktop** - always quit gracefully
3. **Regular cleanup:**
   ```bash
   docker system prune -a --volumes
   ```
   (Only when you don't need existing containers/images)

## Still Having Issues?

1. **Check Docker Desktop logs:**
   - Docker Desktop → Troubleshoot → View logs

2. **Check system resources:**
   - Ensure you have enough disk space
   - Check Activity Monitor for Docker processes

3. **Reinstall Docker Desktop:**
   - Download latest from docker.com
   - Uninstall current version
   - Install fresh copy

## Verification

After fixing, verify everything works:

```bash
# Check Docker
docker info

# Check Docker Compose
docker compose config

# Start project
./docker.sh start

# Check status
./docker.sh status
```

