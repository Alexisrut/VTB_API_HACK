# Backend Testing Guide

## Overview

This document describes how to run and write tests for the backend API.

## Quick Start

### Run All Tests

```bash
# Using the test script
./run_tests.sh

# Or directly with pytest
pytest tests/ -v
```

### Run Tests with Coverage

```bash
./run_tests.sh --coverage
# or
pytest tests/ --cov=app --cov-report=html
```

## Test Structure

```
tests/
├── __init__.py
├── conftest.py          # Pytest fixtures and configuration
├── test_auth.py         # Authentication tests
├── test_health.py        # Health check tests
└── README.md            # Detailed test documentation
```

## Running Tests

### Basic Commands

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_auth.py

# Run specific test
pytest tests/test_auth.py::TestRegistration::test_register_success

# Run with coverage report
pytest --cov=app --cov-report=html --cov-report=term
```

### Running Tests in Docker

```bash
# Run tests inside the app container
docker compose exec app pytest tests/ -v

# Or install dependencies and run locally
docker compose exec app pip install pytest pytest-asyncio pytest-cov aiosqlite httpx
docker compose exec app pytest tests/ -v
```

## Test Coverage

Current test coverage includes:

- ✅ User Registration
  - Successful registration
  - Duplicate email/phone validation
  - Invalid input validation
  - Password strength validation

- ✅ User Login
  - Successful login
  - Invalid credentials
  - Inactive user handling

- ✅ Token Management
  - Token refresh
  - Invalid token handling

- ✅ User Info
  - Get current user
  - Authentication required
  - Invalid token handling

## Writing New Tests

### Example Test

```python
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_my_endpoint(client: AsyncClient):
    """Test description"""
    response = await client.get("/my-endpoint")
    assert response.status_code == 200
    data = response.json()
    assert "expected_field" in data
```

### Available Fixtures

- `client`: AsyncClient instance for making API requests
- `db_session`: Database session (fresh for each test)
- `test_user`: Pre-created test user

### Test Database

Tests use an in-memory SQLite database, so:
- No external database setup required
- Each test gets a fresh database
- Tests run in isolation
- Fast execution

## Troubleshooting

### Database Connection Errors

If you see database connection errors:
1. Ensure PostgreSQL is running: `docker compose ps postgres`
2. Check DATABASE_URL in `.env` file
3. Verify database exists: `docker compose exec postgres psql -U fastapi_user -d fastapi_db -c "\l"`

### Import Errors

If you see import errors:
1. Ensure you're in the project root directory
2. Install dependencies: `pip install -r requirements.txt`
3. Check Python path: `export PYTHONPATH=$PWD`

### Validation Errors (422)

If registration/login returns 422:
- Check request format matches schema
- Phone must be: `+7XXXXXXXXXX` (11 digits after +7)
- Password must have: uppercase, lowercase, digit, min 8 chars
- Email must be valid format
- All required fields must be present

## Test Data

Test users are created automatically in fixtures. Default test user:
- Email: `test@example.com`
- Phone: `+79991234567`
- Password: `TestPass123`
- Active: `True`

## Continuous Integration

To add tests to CI/CD:

```yaml
# Example GitHub Actions
- name: Run tests
  run: |
    pip install -r requirements.txt
    pytest tests/ --cov=app --cov-report=xml
```

## Best Practices

1. **Isolation**: Each test should be independent
2. **Naming**: Use descriptive test names
3. **Assertions**: Be specific about what you're testing
4. **Fixtures**: Reuse fixtures for common setup
5. **Cleanup**: Database is automatically cleaned between tests

## Common Issues

### 422 Unprocessable Entity

This means validation failed. Check:
- Request body format
- Required fields
- Field types and formats
- Validation rules (phone format, password strength, etc.)

### 401 Unauthorized

Token is missing or invalid. Ensure:
- Token is included in Authorization header
- Token format: `Bearer <token>`
- Token hasn't expired

### 500 Internal Server Error

Server error. Check:
- Database connection
- Server logs: `docker compose logs app`
- Error details in response

