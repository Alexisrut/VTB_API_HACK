# Database Connection Fix

## Issue

PostgreSQL was throwing the error: `FATAL: database "fastapi_user" does not exist`

## Root Cause

PostgreSQL defaults to connecting to a database with the same name as the username when no database is specified in the connection string. This can happen with:
- Manual `psql` commands without `-d` flag
- Healthcheck commands
- Some connection attempts

## Solution

1. **Created `fastapi_user` database** - For default connections that don't specify a database name
2. **Updated healthcheck** - Now explicitly specifies the database: `pg_isready -U fastapi_user -d fastapi_db`
3. **Main database remains `fastapi_db`** - This is what the application uses

## Current Database Setup

- `fastapi_db` - Main application database (used by the app)
- `fastapi_user` - Default database for connections without explicit database name
- Both databases are owned by `fastapi_user` user

## Verification

Check databases:
```bash
docker compose exec postgres psql -U fastapi_user -d fastapi_db -c "\l"
```

Test connection:
```bash
docker compose exec postgres psql -U fastapi_user -d fastapi_db -c "SELECT version();"
```

## If Issue Persists

Run the fix script:
```bash
./fix_database.sh
```

Or manually create the database:
```bash
docker compose exec postgres psql -U fastapi_user -d postgres -c "CREATE DATABASE fastapi_user OWNER fastapi_user;"
```

